import json
import httpx
from typing import Dict, Any, List, AsyncGenerator
from app.inference.backend import InferenceBackend
from app.config import settings

class VLLMBackend(InferenceBackend):
    """vLLM specific backend implementation."""

    def __init__(self):
        self.model_name = settings.MODEL_NAME
        self.endpoint = settings.MODAL_ENDPOINT_URL
        if not self.endpoint.endswith("/"):
            self.endpoint += "/"

    def _format_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Manually format messages into ChatML string format since the custom API only accepts a prompt string."""
        prompt = ""
        for m in messages:
            prompt += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        return prompt

    def _build_payload(self, messages: List[Dict[str, Any]], stream: bool, **kwargs) -> Dict[str, Any]:
        prompt = self._format_prompt(messages)
        payload = {"prompt": prompt, "stream": stream}
        
        # Map common OpenAI kwargs to vLLM SamplingParams
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
            
        # Support JSON schema validation if requested
        if "response_format" in kwargs and kwargs["response_format"].get("type") == "json_schema":
            schema = kwargs["response_format"]["json_schema"]["schema"]
            payload["guided_json"] = json.dumps(schema)
            
        return payload

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        payload = self._build_payload(messages, stream=False, **kwargs)
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            
        # The custom snippet returns {"text": ["..."]}
        text = data["text"][0] if data.get("text") else ""
        
        # Wrap into OpenAI-like response object for the orchestrator
        return {
            "choices": [
                {
                    "message": {
                        "content": text
                    }
                }
            ]
        }

    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, stream=True, **kwargs)

        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", self.endpoint, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield data["text"]

    async def health_check(self) -> Dict[str, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Custom snippet doesn't explicitly define a health endpoint,
                # but a simple GET to the root can serve as a ping.
                response = await client.get(self.endpoint)
                return {"status": "healthy" if response.status_code != 500 else "unhealthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "backend": "vllm",
            "context_length": settings.MAX_CONTEXT_LENGTH
        }
