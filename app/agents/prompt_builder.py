from typing import Callable, Awaitable, Optional

from app.agents.base_agent import BaseAgent
from app.inference.client import InferenceClient
from app.schemas.prompt_builder import PromptBuilderResult

PROMPT_BUILDER_SYSTEM_INSTRUCTION = """
You are an expert Prompt Engineer for an autonomous coding swarm.
Your job is to take a raw, often brief, user request and expand it into a highly detailed, structured, and comprehensive prompt.
This enhanced prompt will be passed to a downstream Planner Agent.

You have access to the repository context. 
Your output MUST include:
1. A clear restatement of the goal.
2. A list of specific constraints or requirements inferred from the request.
3. Explicit pointers to relevant files or components found in the context.
4. Step-by-step guidance or considerations for the downstream Planner.

Output your result as a JSON object matching the requested schema.
"""

class PromptBuilderAgent(BaseAgent):
    """Agent responsible for expanding user requests into structured, detailed prompts."""
    
    def __init__(self, inference_client: InferenceClient):
        super().__init__(
            name="PromptBuilder",
            system_instruction=PROMPT_BUILDER_SYSTEM_INSTRUCTION,
            inference_client=inference_client
        )
        
    async def build_prompt(
        self, 
        context_payload: str, 
        user_request: str,
        on_thought: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> PromptBuilderResult:
        """Takes raw user request and context, returns an enhanced prompt."""
        
        user_message = (
            f"Please expand the following raw user request into a comprehensive prompt for the Planner agent.\n\n"
            f"RAW USER REQUEST:\n{user_request}\n"
        )
        
        messages = self.build_messages(context_payload, user_message)
        
        result = await self.inference_client.generate_structured(
            messages=messages,
            schema=PromptBuilderResult,
            on_thought=on_thought
        )
        
        return result
