import logging
import time
import uuid
from typing import Dict, Any, List

from app.config import settings
from app.inference.sglang_backend import SGLangBackend
from app.inference.vllm_backend import VLLMBackend
from app.inference.backend import InferenceBackend

# Configure Python logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InferenceClient:
    """Single entry point for the rest of the system to interact with models."""

    def __init__(self):
        self.backend: InferenceBackend
        if settings.BACKEND_TYPE == "sglang":
            self.backend = SGLangBackend()
        elif settings.BACKEND_TYPE == "vllm":
            self.backend = VLLMBackend()
        else:
            raise ValueError(f"Unknown backend type: {settings.BACKEND_TYPE}")

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            response = await self.backend.chat(messages, **kwargs)
            latency = time.time() - start_time
            
            # Structured logging
            logger.info("Chat request successful", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": settings.BACKEND_TYPE,
                "model": settings.MODEL_NAME
            })
            return response
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Chat request failed: {str(e)}", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": settings.BACKEND_TYPE,
                "model": settings.MODEL_NAME
            })
            # Return structured JSON for failures, no stack traces
            return {
                "error": "Model failure",
                "details": str(e)
            }

    from typing import AsyncGenerator

    async def chat_stream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[str, None]:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            async for chunk in self.backend.chat_stream(messages, **kwargs):
                yield chunk
                
            latency = time.time() - start_time
            logger.info("Chat stream successful", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": settings.BACKEND_TYPE,
                "model": settings.MODEL_NAME
            })
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Chat stream failed: {str(e)}", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": settings.BACKEND_TYPE,
                "model": settings.MODEL_NAME
            })
            raise e

    async def health_check(self) -> Dict[str, str]:
        return await self.backend.health_check()

    async def model_info(self) -> Dict[str, Any]:
        return await self.backend.model_info()
