from typing import List
import logging
from app.inference.client import InferenceClient
from app.agents.planner_agent import PlannerAgent
from app.agents.executor_agent import ExecutorAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.repair_agent import RepairAgent
from app.agents.prompt_builder import PromptBuilderAgent
from app.agents.release_assistant_agent import ReleaseAssistantAgent
from app.orchestration.event_bus import EventBus
from app.orchestration.swarm_state import SwarmState
from app.orchestration.task_router import TaskRouter
from app.orchestration.scheduler import Scheduler
from app.schemas.reviewer import ReviewDecision
from app.schemas.failure import FailureReport
from app.schemas.repair import RepairPlan
from app.memory.agent_memory import SwarmMemory

from app.sandbox.executor import SandboxExecutor
from app.tools.collect_evidence import collect_evidence
from app.tools.apply_patch import apply_patch

logger = logging.getLogger(__name__)

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
        self.prompt_builder = PromptBuilderAgent(self.client)
        self.release_assistant = ReleaseAssistantAgent(self.client)
        
        self.router = TaskRouter(self.executors)
        self.scheduler = Scheduler()
        self.sandbox = SandboxExecutor()
        self.memory = SwarmMemory()

    def _generate_error_signature(self, tool: str, stdout: str, stderr: str) -> str:
        import re
        import hashlib
        logs = (stdout + "\n" + stderr).strip()
        logs = logs.replace("\\", "/")
        # Strip absolute path directories, leaving only file basenames
        logs = re.sub(r'(?:[a-zA-Z]:)?/(?:[^/":]*/)+([^/":\s]+\.[a-zA-Z0-9]+)', r'\1', logs)
        logs = re.sub(r':\d+(:\d+)?', '', logs)
        logs = re.sub(r', line \d+', '', logs)
        logs = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?', '', logs)
        lines = [line.strip() for line in logs.splitlines() if line.strip()]
        cleaned_lines = []
        for line in lines:
            if any(stat in line for stat in ["failed in", "passed in", "=== ", "--- ", "Duration:", "Finished in"]):
                continue
            cleaned_lines.append(line)
            if len(cleaned_lines) > 10:
                break
        sig_text = f"{tool}\n" + "\n".join(cleaned_lines)
        return hashlib.sha256(sig_text.encode('utf-8')).hexdigest()

    async def on_thought_chunk(self, chunk: str):
        await self.event_bus.publish("MODEL_THINKING", chunk)

    async def generate_plan(self, user_request: str):
        """Phase 1: Planning Mode"""
        await self.event_bus.publish("WORKFLOW_STARTED", user_request)
        await self.run_prompt_builder(user_request)
        await self.run_planner(self.state.enhanced_prompt)
        
    async def execute_plan(self) -> ReviewDecision:
        """Phase 2: Execution Mode"""
        if not self.state.plan:
            raise ValueError("No plan has been generated.")
            
        await self.run_executors()
        
        # Self-Healing Loop
        with self.sandbox.fs.create_isolated_workspace(".") as workspace:
            await self.event_bus.publish("EXECUTION_STARTED", workspace)
            
            # Apply initial patches proposed by executors
            for result in self.state.executor_results:
                if hasattr(result, "proposed_patch") and result.proposed_patch:
                    await apply_patch(result.proposed_patch, workspace, self.sandbox)
            
            last_error_sig = None
            last_proposed_fix = None
            last_files_affected = None
            
            while self.state.repair_attempts < MAX_REPAIR_LOOPS:
                await self.event_bus.publish("TESTS_STARTED")
                evidence = await collect_evidence(workspace, self.sandbox)
                self.state.evidence = evidence
                await self.event_bus.publish("TESTS_COMPLETED", evidence)
                
                # Check for failure
                is_healthy = evidence.tests_failed == 0 and evidence.mypy_passed and evidence.ruff_passed
                
                # If we had a previous error we tried to fix, and the signature changed or tests passed, record it!
                if last_error_sig:
                    current_sig = self._generate_error_signature("pytest" if evidence.tests_failed > 0 else "linter", evidence.stdout, evidence.stderr) if not is_healthy else None
                    if is_healthy or current_sig != last_error_sig:
                        self.memory.record_repair(last_error_sig, last_proposed_fix, last_files_affected)
                        last_error_sig = None
                
                if is_healthy:
                    break
                    
                self.state.repair_attempts += 1
                tool = "pytest" if evidence.tests_failed > 0 else "linter"
                failure = FailureReport(
                    tool=tool,
                    error_type="ExecutionError",
                    message="Tests or linters failed."
                )
                self.state.failure_reports.append(failure)
                
                error_sig = self._generate_error_signature(tool, evidence.stdout, evidence.stderr)
                cached = self.memory.lookup_repair(error_sig)
                
                if cached:
                    repair_plan = RepairPlan(
                        failure_reason=f"Cached repair from agent memory for signature: {error_sig}",
                        affected_files=cached["files_affected"],
                        proposed_fix=cached["proposed_fix"],
                        confidence=1.0
                    )
                    logger.info(f"Applying cached repair for signature: '{error_sig}'")
                else:
                    await self.event_bus.publish("REPAIR_STARTED", failure)
                    repair_plan = await self.repair.generate_repair(self.context_payload, failure, evidence, self.on_thought_chunk)
                    
                    # Track this LLM attempt to record it if the next iteration succeeds/changes signature
                    last_error_sig = error_sig
                    last_proposed_fix = repair_plan.proposed_fix
                    last_files_affected = repair_plan.affected_files
                
                await apply_patch(repair_plan.proposed_fix, workspace, self.sandbox)
                await self.event_bus.publish("REPAIR_COMPLETED", repair_plan)
            
            await self.event_bus.publish("EXECUTION_COMPLETED", self.state.evidence)
            
            # Run reviewer inside the workspace context while files are present
            await self.run_reviewer()
            
            # If approved, write files back to the host repository
            if self.state.review and self.state.review.approved:
                import os
                import shutil
                for f in self.state.evidence.files_modified:
                    src = os.path.join(workspace, f)
                    dst = os.path.join(".", f)
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
        return self.return_result()
        
    async def receive_request(self, user_request: str) -> ReviewDecision:
        """Convenience method to run both planning and execution in one go."""
        await self.generate_plan(user_request)
        return await self.execute_plan()

    async def run_prompt_builder(self, request: str):
        await self.event_bus.publish("PROMPT_BUILDER_STARTED", None)
        result = await self.prompt_builder.build_prompt(self.context_payload, request, self.on_thought_chunk)
        self.state.enhanced_prompt = result.enhanced_prompt
        await self.event_bus.publish("PROMPT_BUILDER_COMPLETED", result.enhanced_prompt)

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

    async def run_release_assistant(self, pr_context: str):
        from app.schemas.release_assistant import ReleaseReport
        # If the input is a URL, we try to scrape it or at least use it
        # Real-world use might fetch a git diff using httpx here.
        # Since scrape_url is handy, we can use it if it's a URL.
        if pr_context.startswith("http"):
            from app.tools.scrape_url import scrape_url
            scraped_content = await scrape_url(pr_context)
            pr_context = f"PR URL: {pr_context}\n\nContent:\n{scraped_content}"
            
        await self.event_bus.publish("WORKFLOW_STARTED", "Release Readiness Review")
        report = await self.release_assistant.analyze_pr(self.context_payload, pr_context, self.on_thought_chunk)
        await self.event_bus.publish("TASK_COMPLETED", [report])
        return report
