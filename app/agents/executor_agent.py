from app.agents.base_agent import BaseAgent
from app.schemas.planner import Task
from app.schemas.executor import ExecutorResult

class ExecutorAgent(BaseAgent):
    """Analyzes repository context and proposes file modifications."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompt = "You are an Executor Agent. Propose code modifications using the proposed_patch field (in unified diff format) without attempting to review or repair them."

    from typing import Callable, Awaitable, Optional

    async def execute_task(self, context_payload: str, task: Task, stream_callback: Optional[Callable[[str], Awaitable[None]]] = None) -> ExecutorResult:
        prompt = (
            f"Execute the following task:\n"
            f"Task ID: {task.id}\n"
            f"Title: {task.title}\n"
            f"Description: {task.description}\n"
            f"Target Files: {task.target_files}\n\n"
            "Generate a unified diff/patch for the code changes and return it in the proposed_patch field. Make sure the diff paths match target files exactly so it can be applied with git apply."
        )
        return await self.run(context_payload, prompt, ExecutorResult, stream_callback)

