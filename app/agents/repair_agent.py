from app.agents.base_agent import BaseAgent
from app.schemas.repair import RepairPlan
from app.schemas.failure import FailureReport
from app.schemas.evidence import ExecutionEvidence

class RepairAgent(BaseAgent):
    """Analyzes failures and generates corrective patches."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompt = "You are a Repair Agent. You only fix failures based on evidence. Do not create new features."

    async def generate_repair(self, context_payload: str, failure: FailureReport, evidence: ExecutionEvidence) -> RepairPlan:
        prompt = (
            f"Generate a repair plan for the following failure:\n"
            f"Failure: {failure.model_dump_json()}\n"
            f"Execution Evidence: {evidence.model_dump_json()}\n"
        )
        return await self.run(context_payload, prompt, RepairPlan)
