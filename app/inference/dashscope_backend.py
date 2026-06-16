import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

from app.inference.backend import InferenceBackend
from app.config import settings

logger = logging.getLogger(__name__)

class DashScopeBackend(InferenceBackend):
    """DashScope (Qwen Cloud) compatible backend implementation."""

    def __init__(self):
        base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        api_key = settings.OPENAI_API_KEY or "fake-key"
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=600.0,
        )
        
        # Format model name for DashScope compatible mode
        # Qwen/Qwen2.5-7B-Instruct -> qwen2.5-7b-instruct
        model = settings.MODEL_NAME
        if "/" in model:
            model = model.split("/")[-1]
        model_lower = model.lower()
        
        # Map common HF/OS Qwen models to DashScope commercial models (useful for international endpoint)
        fallback_map = {
            "qwen2.5-7b-instruct": "qwen-plus",
            "qwen2.5-14b-instruct": "qwen-plus",
            "qwen2.5-72b-instruct": "qwen-max",
            "qwen2.5-coder-7b-instruct": "qwen-coder-plus",
            "qwen2.5-coder-32b-instruct": "qwen-coder-plus",
            "qwen2.5-coder-1.5b-instruct": "qwen-coder-plus",
        }
        
        self.model_name = fallback_map.get(model_lower, model_lower)
        logger.info(f"Initialized DashScopeBackend (base_url: {base_url}). Mapped '{settings.MODEL_NAME}' to '{self.model_name}'.")


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
            await self.client.models.list()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model": settings.MODEL_NAME,
            "backend": "dashscope",
            "context_length": settings.MAX_CONTEXT_LENGTH
        }

