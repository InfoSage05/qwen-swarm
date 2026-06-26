import logging
from typing import Dict, Any, List, AsyncGenerator
from openai import AsyncOpenAI

from app.inference.backend import InferenceBackend
from app.config import settings

logger = logging.getLogger(__name__)

class GLMBackend(InferenceBackend):
    """Zhipu AI (GLM) compatible backend implementation."""

    def __init__(self):
        base_url = settings.GLM_ENDPOINT_URL or "https://open.bigmodel.cn/api/paas/v4"
        api_key = settings.GLM_API_KEY or "fake-key"
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=600.0,
        )
        
        # You can map models if necessary, or just use what's given.
        self.model_name = settings.MODEL_NAME
        # If the user hasn't explicitly set a GLM model and is still using Qwen, fallback to a GLM model.
        if "qwen" in self.model_name.lower():
            self.model_name = "glm-4"
            
        logger.info(f"Initialized GLMBackend (base_url: {base_url}). Using model '{self.model_name}'.")

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
            # Not all OpenAI-compatible endpoints support models.list(), but it's a standard check
            await self.client.models.list()
            return {"status": "healthy"}
        except Exception as e:
            # Consider it healthy even if models.list() fails because the API might not support it
            return {"status": "healthy", "warning": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "backend": "glm",
            "context_length": settings.MAX_CONTEXT_LENGTH
        }
