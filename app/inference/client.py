import os
import logging
import time
import uuid
from typing import Dict, Any, List

from app.config import settings
from app.inference.sglang_backend import SGLangBackend
from app.inference.vllm_backend import VLLMBackend
from app.inference.backend import InferenceBackend

# Configure Python logging to a file to prevent polluting terminal output
log_dir = ".repopilot"
try:
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(log_dir, "swarm.log"),
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
except Exception:
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
        elif settings.BACKEND_TYPE == "dashscope":
            from app.inference.dashscope_backend import DashScopeBackend
            self.backend = DashScopeBackend()
        elif settings.BACKEND_TYPE == "glm":
            from app.inference.glm_backend import GLMBackend
            self.backend = GLMBackend()
        elif settings.BACKEND_TYPE == "ollama":
            from app.inference.ollama_backend import OllamaBackend
            self.backend = OllamaBackend()
        else:
            raise ValueError(f"Unknown backend type: {settings.BACKEND_TYPE}")
            
        # Optional Vision Backend Initialization
        self.vision_backend = None
        if settings.OPENROUTER_API_KEY:
            from app.inference.openrouter_backend import OpenRouterBackend
            self.vision_backend = OpenRouterBackend()

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

    async def vision_chat(self, messages: List[Dict[str, Any]], image_url: str, **kwargs) -> Dict[str, Any]:
        """
        Specialized method to process multi-modal requests using OpenRouter Vision Models.
        Formats the last message to include the image payload natively.
        """
        if not self.vision_backend:
            raise ValueError("Vision backend is not initialized. Please set OPENROUTER_API_KEY.")
            
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Format the last message content into OpenAI's multimodal array format
        last_msg = messages[-1]
        text_content = last_msg["content"]
        
        last_msg["content"] = [
            {"type": "text", "text": text_content},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
        
        try:
            response = await self.vision_backend.chat(messages, **kwargs)
            latency = time.time() - start_time
            
            logger.info("Vision Chat request successful", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": "openrouter",
                "model": settings.VISION_MODEL_NAME
            })
            return response
            
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Vision Chat request failed: {str(e)}", extra={
                "request_id": request_id,
                "latency": latency,
                "backend": "openrouter",
                "model": settings.VISION_MODEL_NAME
            })
            return {
                "error": "Vision Model failure",
                "details": str(e)
            }

    async def health_check(self) -> Dict[str, str]:
        return await self.backend.health_check()

    async def model_info(self) -> Dict[str, Any]:
        return await self.backend.model_info()
