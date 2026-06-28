import json
from typing import Dict, Any, List, Type
from pydantic import BaseModel

from app.inference.client import InferenceClient

class BaseAgent:
    """Base class providing shared behavior for all swarm agents."""
    
    def __init__(self, inference_client: InferenceClient):
        self.client = inference_client
        self.system_prompt = "You are a specialized software engineering agent."
        
    def build_messages(self, context_payload: str, user_prompt: str) -> List[Dict[str, str]]:
        """Constructs prefix-cache compliant messages."""
        # 1. Identical prefix for all agents to maximize Radix/KV cache hits
        shared_system_content = "You are a specialized software engineering agent. You must respond in valid JSON format."
            
        messages = [
            {"role": "system", "content": shared_system_content},
            {"role": "user", "content": f"Repository Context:\n{context_payload}"}
        ]
        
        # 2. Agent-specific divergence at the end of the prompt
        agent_instruction = f"Your Role: {self.system_prompt}\n\nTask: {user_prompt}"
        messages.append({"role": "user", "content": agent_instruction})
        
        return messages
        
    from typing import Callable, Awaitable, Optional

    async def run(self, context_payload: str, user_prompt: str, schema_class: Type[BaseModel], stream_callback: Optional[Callable[[str], Awaitable[None]]] = None, temperature: float = 0.3) -> BaseModel:
        messages = self.build_messages(context_payload, user_prompt)
        schema = schema_class.model_json_schema()
        
        if stream_callback:
            accumulated_json = ""
            async for chunk in self.client.chat_stream(
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"schema": schema, "name": schema_class.__name__}},
                temperature=temperature
            ):
                accumulated_json += chunk
                await stream_callback(chunk)
                
            response = {"choices": [{"message": {"content": accumulated_json}}]}
            return self.validate_response(response, schema_class)
        else:
            response = await self.client.chat(
                messages=messages,
                response_format={"type": "json_schema", "json_schema": {"schema": schema, "name": schema_class.__name__}},
                temperature=temperature
            )
            return self.validate_response(response, schema_class)
        
    def validate_response(self, response: Dict[str, Any], schema_class: Type[BaseModel]) -> BaseModel:
        if "error" in response:
            raise ValueError(f"Backend failure: {response['details']}")
            
        try:
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            import logging
            logging.getLogger(__name__).info(f"Agent {schema_class.__name__} returned structured output: {parsed}")
            return schema_class(**parsed)
        except Exception as e:
            raise ValueError(f"Failed to validate structured output: {str(e)}\nResponse: {response}")

