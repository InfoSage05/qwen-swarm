import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError

class ConfigurationError(Exception):
    """Raised when there is a critical configuration issue."""
    pass

class Settings(BaseSettings):
    """
    Centralized configuration for the RepoPilot Inference Foundation.
    Loads values from environment variables, ~/.config/repopilot/config.toml, or a .env file.
    """
    DASHSCOPE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    MODAL_ENDPOINT_URL: Optional[str] = "http://localhost:30000"
    MODEL_NAME: Optional[str] = "Qwen/Qwen2.5-7B-Instruct"
    BACKEND_TYPE: Optional[str] = "sglang"  # Options: sglang, vllm, dashscope, glm, ollama, mock
    GLM_API_KEY: Optional[str] = None
    GLM_ENDPOINT_URL: Optional[str] = "https://api.z.ai/api/coding/paas/v4"
    OPENROUTER_API_KEY: Optional[str] = None

    # Load from env vars, fallback to .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @classmethod
    def load(cls) -> "Settings":
        """Loads settings, incorporating ~/.config/repopilot/config.toml if it exists."""
        # For simplicity, if you want TOML loading natively, you can use tomllib (Python 3.11+)
        # We'll just rely on Pydantic's default mechanisms + .env for now, and handle TOML merging if needed.
        # But per requirements: "Load from: (1) environment variables, (2) ~/.config/repopilot/config.toml, (3) .env"
        # Since pydantic-settings handles env and .env, we can just parse TOML manually.
        
        config_path = Path.home() / ".config" / "repopilot" / "config.toml"
        toml_data = {}
        if config_path.exists():
            import tomllib
            with open(config_path, "rb") as f:
                try:
                    toml_data = tomllib.load(f)
                except Exception:
                    pass
                    
        # Apply TOML values to os.environ conditionally if not already set, 
        # so they take precedence over .env but not over actual env vars
        # Pydantic loads in this order: Env vars -> dotenv -> defaults
        # We can just instantiate and then override.
        settings = cls()
        for k, v in toml_data.items():
            if hasattr(settings, k.upper()):
                # Only override if the env var wasn't set (we can check os.environ directly)
                if k.upper() not in os.environ:
                    setattr(settings, k.upper(), v)
                    
        return settings

    def validate_backend(self):
        """Validates that the selected backend has its required API key."""
        backend = (self.BACKEND_TYPE or "").lower()
        if backend == "dashscope" and not self.DASHSCOPE_API_KEY:
            raise ConfigurationError(
                "Backend is set to 'dashscope' but DASHSCOPE_API_KEY is not configured. "
                "Please run `repopilot setup` or set it in your .env file (see .env.example)."
            )
        elif backend == "glm" and not self.GLM_API_KEY:
            raise ConfigurationError(
                "Backend is set to 'glm' but GLM_API_KEY is not configured. "
                "Please run `repopilot setup` or set it in your .env file."
            )
        elif backend == "vllm" and not self.OPENAI_API_KEY:
            raise ConfigurationError(
                "Backend is set to 'vllm' but OPENAI_API_KEY is missing. "
                "Please set it in your .env file."
            )

# Global configuration instance
settings = Settings.load()
