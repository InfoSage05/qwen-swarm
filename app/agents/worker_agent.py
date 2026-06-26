from typing import Callable, Any, Awaitable, List
import logging

from app.inference.client import InferenceClient
from app.schemas.conductor import WorkerResponse

logger = logging.getLogger(__name__)

WORKER_SYSTEM_PROMPT = """
You are a highly capable AI agent in a cooperative swarm. You have been assigned a specific subtask by the Swarm Conductor.
Your goal is to execute the assigned subtask to the best of your ability.

You are provided with:
1. The original user request.
2. The semantic repository context.
3. The specific SUBTASK assigned to you.
4. (Optional) Previous responses from other agents in the swarm if they are relevant to your subtask.

You must output your response according to the provided JSON schema.
- If your subtask involves writing or modifying code, please provide the complete unified diff format in the 'proposed_patch' field, and explain your logic in the 'response' field.
- If your subtask is purely analytical, planning, or reviewing, put your entire answer in the 'response' field and leave 'proposed_patch' empty.
"""

class WorkerAgent:
    """A generic, dynamic agent that executes subtasks assigned by the Conductor."""
    
    def __init__(self, inference_client: InferenceClient):
        self.client = inference_client

    async def execute_subtask(
        self,
        context_payload: str,
        user_request: str,
        subtask: str,
        past_responses: List[str],
        on_chunk: Callable[[str], Awaitable[None]] = None
    ) -> WorkerResponse:
        
        user_content = f"ORIGINAL USER REQUEST:\n{user_request}\n\nREPOSITORY CONTEXT:\n{context_payload}\n\n"
        
        if past_responses:
            user_content += "--- PREVIOUS AGENT RESPONSES ---\n"
            for i, past in enumerate(past_responses):
                user_content += f"Agent {i} Output:\n{past}\n\n"
            user_content += "--------------------------------\n\n"
            
        user_content += f"YOUR ASSIGNED SUBTASK:\n{subtask}"
        
        messages = [
            {"role": "system", "content": WORKER_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_content}
        ]
        
        response = await self.client.chat(
            messages=messages,
            response_format=WorkerResponse,
            temperature=0.3,
            on_chunk=on_chunk
        )
        
        try:
            return WorkerResponse.model_validate(response)
        except Exception as e:
            logger.error(f"Failed to parse Worker Response: {e}")
            return WorkerResponse(response=str(response))

    async def execute_vision_subtask(
        self,
        context_payload: str,
        user_request: str,
        subtask: str,
        past_responses: List[str],
        image_url: str,
        on_chunk: Callable[[str], Awaitable[None]] = None
    ) -> WorkerResponse:
        
        user_content = f"ORIGINAL USER REQUEST:\n{user_request}\n\nREPOSITORY CONTEXT:\n{context_payload}\n\n"
        
        if past_responses:
            user_content += "--- PREVIOUS AGENT RESPONSES ---\n"
            for i, past in enumerate(past_responses):
                user_content += f"Agent {i} Output:\n{past}\n\n"
            user_content += "--------------------------------\n\n"
            
        user_content += f"YOUR ASSIGNED SUBTASK (Analyze the attached image):\n{subtask}"
        
        messages = [
            {"role": "system", "content": WORKER_SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_content}
        ]
        
        response = await self.client.vision_chat(
            messages=messages,
            image_url=image_url,
            response_format=WorkerResponse,
            temperature=0.3,
            on_chunk=on_chunk
        )
        
        try:
            return WorkerResponse.model_validate(response)
        except Exception as e:
            logger.error(f"Failed to parse Vision Worker Response: {e}")
            return WorkerResponse(response=str(response))
