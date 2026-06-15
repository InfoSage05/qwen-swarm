from typing import Dict, Any, List
from app.inference.backend import InferenceBackend
from app.config import settings

class VLLMBackend(InferenceBackend):
    """vLLM specific backend implementation skeleton."""

    def __init__(self):
        self.model_name = settings.MODEL_NAME

    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("vLLM chat is not fully implemented yet.")

    async def health_check(self) -> Dict[str, str]:
        return {"status": "unimplemented"}

    async def model_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "backend": "vllm",
            "context_length": settings.MAX_CONTEXT_LENGTH
        }
