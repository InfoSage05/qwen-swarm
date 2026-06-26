from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Centralized configuration for the RepoPilot Inference Foundation.
    Loads values from environment variables or a .env file.
    """
    MODEL_NAME: str = "Qwen/Qwen2.5-7B-Instruct"
    BACKEND_TYPE: str = "sglang"  # Options: sglang, vllm
    MODAL_APP_NAME: str = "qwen-swarm-sglang"
    GPU_TYPE: str = "a10g"
    MAX_CONTEXT_LENGTH: int = 32768
    SGLANG_HOST: str = "0.0.0.0"
    SGLANG_PORT: int = 30000
    
    # URL to the exposed endpoint
    MODAL_ENDPOINT_URL: str = "http://localhost:30000"

    # API key for the inference service
    OPENAI_API_KEY: str = "swarm-key"
    
    # Zhipu AI / GLM Integration
    GLM_API_KEY: Optional[str] = "c40400ea21914321a3243a8c69c09dd9.NiRTqvSX9a5zCb6W"
    GLM_ENDPOINT_URL: Optional[str] = "https://api.z.ai/api/coding/paas/v4"

    # Multi-Modal Vision Model Integration via OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    VISION_MODEL_NAME: str = "qwen/qwen-2-vl-7b-instruct:free"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Global configuration instance
settings = Settings()
