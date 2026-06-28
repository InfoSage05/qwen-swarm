import ollama
from typing import Dict, Any, List, AsyncGenerator
from app.inference.backend import InferenceBackend
from app.config import settings

class OllamaBackend(InferenceBackend):
    def __init__(self):
        host = getattr(settings, 'OLLAMA_HOST', 'http://localhost:11434')
        self.client = ollama.AsyncClient(host=host)

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        call_kwargs = {
            "model": settings.MODEL_NAME,
            "messages": messages,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            }
        }
        
        response_format = kwargs.get("response_format")
        if response_format:
            if hasattr(response_format, 'model_json_schema'):
                call_kwargs["format"] = response_format.model_json_schema()
            else:
                call_kwargs["format"] = "json"

        response = await self.client.chat(**call_kwargs)
        
        return {
            "choices": [{
                "message": {
                    "content": response['message']['content']
                }
            }]
        }

    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        call_kwargs = {
            "model": settings.MODEL_NAME,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            }
        }
        
        async for chunk in await self.client.chat(**call_kwargs):
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']

    async def health_check(self) -> Dict[str, str]:
        try:
            await self.client.list()
            return {"status": "ok", "backend": "ollama"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        return {"model": settings.MODEL_NAME, "backend": "ollama"}
