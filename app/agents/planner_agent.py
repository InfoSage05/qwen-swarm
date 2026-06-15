from app.agents.base_agent import BaseAgent
from app.schemas.planner import Plan

class PlannerAgent(BaseAgent):
    """Transforms a user request into executable tasks."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompt = "You are a Planner Agent. Transform user requests into an executable Plan."

    async def create_plan(self, context_payload: str, request: str) -> Plan:
        prompt = f"User Request: {request}\nAnalyze context and create a structured execution plan."
        return await self.run(context_payload, prompt, Plan)
