from app.agents.base_agent import BaseAgent
from app.schemas.planner import Plan
from app.schemas.evidence import ExecutionEvidence
from app.schemas.reviewer import ReviewDecision

class ReviewerAgent(BaseAgent):
    """Inspects execution evidence and makes the final approval decision."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompt = "You are a Reviewer Agent. Evaluate execution evidence against the original plan. Only approve if tests pass."

    async def review(self, context_payload: str, plan: Plan, evidence: ExecutionEvidence) -> ReviewDecision:
        prompt = (
            f"Review the execution:\n"
            f"Original Plan: {plan.model_dump_json()}\n"
            f"Execution Evidence: {evidence.model_dump_json()}\n"
        )
        return await self.run(context_payload, prompt, ReviewDecision)
