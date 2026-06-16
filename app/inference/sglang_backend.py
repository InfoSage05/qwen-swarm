from typing import Dict, Any, List
from openai import AsyncOpenAI

from app.inference.backend import InferenceBackend
from app.config import settings

class SGLangBackend(InferenceBackend):
    """SGLang specific backend implementation."""

    def __init__(self):
        url = settings.MODAL_ENDPOINT_URL
        if url.endswith("/v1"):
            base_url = url
        elif url.endswith("/v1/"):
            base_url = url.rstrip("/")
        else:
            base_url = f"{url.rstrip('/')}/v1"

        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=base_url,
            timeout=600.0,
        )
        self.model_name = settings.MODEL_NAME

    from typing import AsyncGenerator

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return response.model_dump()

    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        kwargs["stream"] = True
        response_stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        async for chunk in response_stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

    async def health_check(self) -> Dict[str, str]:
        try:
            # Simple check by requesting models list
            await self.client.models.list()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "backend": "sglang",
            "context_length": settings.MAX_CONTEXT_LENGTH
        }
