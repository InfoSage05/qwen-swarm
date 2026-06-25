import json
import logging
from typing import Dict, Any, List, AsyncGenerator
from openai import AsyncOpenAI

from app.config import settings
from app.inference.backend import InferenceBackend

logger = logging.getLogger(__name__)

class OpenRouterBackend(InferenceBackend):
    """
    Inference backend for OpenRouter.
    Specifically useful for free multi-modal/vision models.
    """

    def __init__(self):
        if not settings.OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY is not set. Vision features may fail.")
            
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY or "dummy-key",
        )
        self.model_name = settings.VISION_MODEL_NAME

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        
        # We might need to parse Pydantic response_format if provided
        response_format_class = kwargs.pop("response_format", None)
        if response_format_class:
            # For JSON schema validation
            schema = response_format_class.model_json_schema()
            
            # OpenAI structured outputs / JSON mode
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_format_class.__name__,
                    "schema": schema,
                    "strict": True
                }
            }

        # Some callbacks
        on_chunk = kwargs.pop("on_chunk", None)

        if on_chunk:
            kwargs["stream"] = True

        try:
            if on_chunk:
                response_content = ""
                response_stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
                async for chunk in response_stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        response_content += delta
                        await on_chunk(delta)
                return json.loads(response_content) if response_format_class else {"content": response_content}
            else:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
                content = response.choices[0].message.content
                if response_format_class:
                    return json.loads(content)
                return {"content": content}
        except Exception as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            raise e

    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        kwargs.pop("response_format", None) # Remove it if passed
        
        try:
            response_stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                **kwargs
            )
            async for chunk in response_stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {str(e)}")
            raise e

    async def health_check(self) -> Dict[str, str]:
        return {"status": "ok", "backend": "openrouter"}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": "openrouter"
        }
