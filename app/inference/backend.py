import abc
from typing import Dict, Any, List

class InferenceBackend(abc.ABC):
    """Abstract base class for inference backends."""

    @abc.abstractmethod
    async def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Send a chat request and return the response."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> Dict[str, str]:
        """Check the health of the backend."""
        pass

    @abc.abstractmethod
    async def model_info(self) -> Dict[str, Any]:
        """Retrieve information about the loaded model."""
        pass
