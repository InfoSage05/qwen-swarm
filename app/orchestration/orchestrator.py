import os
import shutil
import re
import hashlib
import logging
from typing import List, Optional

from app.inference.client import InferenceClient
from app.agents.conductor_agent import ConductorAgent
from app.agents.worker_agent import WorkerAgent
from app.agents.repair_agent import RepairAgent
from app.orchestration.event_bus import EventBus
from app.orchestration.swarm_state import SwarmState
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
    """Central coordinator owning the Conductor workflow."""
    
    def __init__(self, context_payload: str, inference_client: InferenceClient):
        self.context_payload = context_payload
        self.client = inference_client
        
        self.event_bus = EventBus()
        self.state = SwarmState()
        
        self.conductor = ConductorAgent(self.client)
        self.worker = WorkerAgent(self.client)
        self.repair = RepairAgent(self.client)
        
        self.sandbox = SandboxExecutor()
        self.memory = SwarmMemory()

    def _generate_error_signature(self, tool: str, stdout: str, stderr: str) -> str:
        logs = (stdout + "\n" + stderr).strip()
        logs = logs.replace("\\", "/")
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

    async def receive_request(self, user_request: str) -> ReviewDecision:
        await self.event_bus.publish("WORKFLOW_STARTED", user_request)
        
        # 1. Conductor dynamically generates the topology and subtasks
        workflow = await self.conductor.create_workflow(self.context_payload, user_request, self.on_thought_chunk)
        
        # Signal the UI that we have a plan (in place of the old PLAN_CREATED)
        # We wrap the workflow in a generic object so the UI can log it.
        class DummyPlan:
            tasks = [{"title": subtask, "description": subtask} for subtask in workflow.subtasks]
        await self.event_bus.publish("PLAN_CREATED", DummyPlan())
        
        past_responses = []
        final_proposed_patch = None
        
        # 2. Iterate through the dynamic workflow
        for step_idx, subtask in enumerate(workflow.subtasks):
            model_id = workflow.model_id[step_idx] if step_idx < len(workflow.model_id) else 0
            access_spec = workflow.access_list[step_idx] if step_idx < len(workflow.access_list) else []
            
            context_responses = []
            if "all" in access_spec or "all" in str(access_spec).lower():
                context_responses = past_responses.copy()
            else:
                for idx in access_spec:
                    if isinstance(idx, int) and idx < len(past_responses):
                        context_responses.append(past_responses[idx])
            
            # Announce task started for UI
            await self.event_bus.publish("TASK_STARTED", [{"task": {"title": subtask}, "agent_id": f"Model {model_id}"}])
            
            # Worker Agent executes the tailored prompt
            worker_response = await self.worker.execute_subtask(
                context_payload=self.context_payload,
                user_request=user_request,
                subtask=subtask,
                past_responses=context_responses,
                on_chunk=self.on_thought_chunk
            )
            
            past_responses.append(worker_response.response)
            
            if worker_response.proposed_patch:
                final_proposed_patch = worker_response.proposed_patch
                
            # Announce task completed for UI
            class DummyResult:
                task = {"title": subtask}
                status = "Success"
                feedback = "Completed dynamically"
            await self.event_bus.publish("TASK_COMPLETED", [DummyResult()])
            
        # 3. Sandbox Verification & Self-Healing Loop
        if final_proposed_patch:
            return await self._run_sandbox_loop(final_proposed_patch)
            
        return ReviewDecision(approved=True, feedback="No code changes proposed.", confidence=1.0)
        
    async def _run_sandbox_loop(self, proposed_patch: str) -> ReviewDecision:
        with self.sandbox.fs.create_isolated_workspace(".") as workspace:
            await self.event_bus.publish("EXECUTION_STARTED", workspace)
            
            await apply_patch(proposed_patch, workspace, self.sandbox)
            
            last_error_sig = None
            last_proposed_fix = None
            last_files_affected = None
            
            while self.state.repair_attempts < MAX_REPAIR_LOOPS:
                await self.event_bus.publish("TESTS_STARTED")
                evidence = await collect_evidence(workspace, self.sandbox)
                self.state.evidence = evidence
                await self.event_bus.publish("TESTS_COMPLETED", evidence)
                
                is_healthy = evidence.tests_failed == 0 and evidence.mypy_passed and evidence.ruff_passed
                
                if last_error_sig:
                    current_sig = self._generate_error_signature("pytest" if evidence.tests_failed > 0 else "linter", evidence.stdout, evidence.stderr) if not is_healthy else None
                    if is_healthy or current_sig != last_error_sig:
                        self.memory.record_repair(last_error_sig, last_proposed_fix, last_files_affected)
                        last_error_sig = None
                        
                if is_healthy:
                    break
                    
                self.state.repair_attempts += 1
                tool = "pytest" if evidence.tests_failed > 0 else "linter"
                failure = FailureReport(tool=tool, error_type="ExecutionError", message="Tests or linters failed.")
                self.state.failure_reports.append(failure)
                
                error_sig = self._generate_error_signature(tool, evidence.stdout, evidence.stderr)
                cached = self.memory.lookup_repair(error_sig)
                
                if cached:
                    repair_plan = RepairPlan(failure_reason=f"Cached repair", affected_files=cached["files_affected"], proposed_fix=cached["proposed_fix"], confidence=1.0)
                else:
                    await self.event_bus.publish("REPAIR_STARTED", failure)
                    repair_plan = await self.repair.generate_repair(self.context_payload, failure, evidence, self.on_thought_chunk)
                    last_error_sig = error_sig
                    last_proposed_fix = repair_plan.proposed_fix
                    last_files_affected = repair_plan.affected_files
                    
                await apply_patch(repair_plan.proposed_fix, workspace, self.sandbox)
                await self.event_bus.publish("REPAIR_COMPLETED", repair_plan)
                
            await self.event_bus.publish("EXECUTION_COMPLETED", self.state.evidence)
            
            is_healthy = self.state.evidence.tests_failed == 0 and self.state.evidence.mypy_passed and self.state.evidence.ruff_passed
            
            if is_healthy:
                for f in self.state.evidence.files_modified:
                    src = os.path.join(workspace, f)
                    dst = os.path.join(".", f)
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        
            return ReviewDecision(approved=is_healthy, feedback="Sandbox execution finished.", confidence=1.0 if is_healthy else 0.0)
