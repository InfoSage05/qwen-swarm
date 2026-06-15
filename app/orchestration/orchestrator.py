from typing import List
from app.inference.client import InferenceClient
from app.agents.planner_agent import PlannerAgent
from app.agents.executor_agent import ExecutorAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.repair_agent import RepairAgent
from app.orchestration.event_bus import EventBus
from app.orchestration.swarm_state import SwarmState
from app.orchestration.task_router import TaskRouter
from app.orchestration.scheduler import Scheduler
from app.schemas.reviewer import ReviewDecision
from app.schemas.failure import FailureReport

from app.sandbox.executor import SandboxExecutor
from app.tools.collect_evidence import collect_evidence
from app.tools.apply_patch import apply_patch

MAX_REPAIR_LOOPS = 3

class SwarmOrchestrator:
    """Central coordinator owning the workflow."""
    
    def __init__(self, context_payload: str, inference_client: InferenceClient):
        self.context_payload = context_payload
        self.client = inference_client
        
        self.event_bus = EventBus()
        self.state = SwarmState()
        
        self.planner = PlannerAgent(self.client)
        self.executors = [ExecutorAgent(self.client) for _ in range(3)]
        self.reviewer = ReviewerAgent(self.client)
        self.repair = RepairAgent(self.client)
        
        self.router = TaskRouter(self.executors)
        self.scheduler = Scheduler()
        self.sandbox = SandboxExecutor()

    async def on_thought_chunk(self, chunk: str):
        await self.event_bus.publish("MODEL_THINKING", chunk)

    async def receive_request(self, user_request: str) -> ReviewDecision:
        """Main entry point for the swarm workflow."""
        await self.event_bus.publish("WORKFLOW_STARTED", user_request)
        
        await self.run_planner(user_request)
        await self.run_executors()
        
        # Self-Healing Loop
        with self.sandbox.fs.create_isolated_workspace(".") as workspace:
            await self.event_bus.publish("EXECUTION_STARTED", workspace)
            
            while self.state.repair_attempts < MAX_REPAIR_LOOPS:
                await self.event_bus.publish("TESTS_STARTED")
                evidence = await collect_evidence(workspace, self.sandbox)
                self.state.evidence = evidence
                await self.event_bus.publish("TESTS_COMPLETED", evidence)
                
                # Check for failure
                if evidence.tests_failed == 0 and evidence.mypy_passed and evidence.ruff_passed:
                    break
                    
                self.state.repair_attempts += 1
                failure = FailureReport(
                    tool="pytest" if evidence.tests_failed > 0 else "linter",
                    error_type="ExecutionError",
                    message="Tests or linters failed."
                )
                self.state.failure_reports.append(failure)
                
                await self.event_bus.publish("REPAIR_STARTED", failure)
                repair_plan = await self.repair.generate_repair(self.context_payload, failure, evidence, self.on_thought_chunk)
                
                await apply_patch(repair_plan.proposed_fix, workspace, self.sandbox)
                await self.event_bus.publish("REPAIR_COMPLETED", repair_plan)
            
            await self.event_bus.publish("EXECUTION_COMPLETED", self.state.evidence)
        
        await self.run_reviewer()
        return self.return_result()

    async def run_planner(self, request: str):
        plan = await self.planner.create_plan(self.context_payload, request, self.on_thought_chunk)
        self.state.plan = plan
        self.state.active_tasks = plan.tasks.copy()
        await self.event_bus.publish("PLAN_CREATED", plan)

    async def run_executors(self):
        if not self.state.plan:
            return
            
        assignments = self.router.assign_tasks(self.state.active_tasks)
        await self.event_bus.publish("TASK_STARTED", assignments)
        
        results = await self.scheduler.run_executors(self.context_payload, assignments, self.on_thought_chunk)
        
        self.state.executor_results = results
        self.state.completed_tasks = self.state.active_tasks.copy()
        self.state.active_tasks.clear()
        
        await self.event_bus.publish("TASK_COMPLETED", results)

    async def run_reviewer(self):
        if not self.state.plan or not self.state.evidence:
            return
            
        await self.event_bus.publish("REVIEW_STARTED")
        decision = await self.reviewer.review(self.context_payload, self.state.plan, self.state.evidence, self.on_thought_chunk)
        self.state.review = decision
        await self.event_bus.publish("REVIEW_COMPLETED", decision)

    def return_result(self) -> ReviewDecision:
        return self.state.review
