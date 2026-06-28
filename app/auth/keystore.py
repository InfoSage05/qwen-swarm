import keyring
import os
from pathlib import Path

SERVICE_NAME = "repopilot"

def save_key(provider: str, key: str) -> None:
    """Save an API key to the OS native keychain."""
    try:
        keyring.set_password(SERVICE_NAME, provider, key)
    except Exception:
        # Fallback to config file if keyring is unavailable
        _fallback_save_key(provider, key)

def load_key(provider: str) -> str | None:
    """Load an API key from the OS native keychain."""
    try:
        key = keyring.get_password(SERVICE_NAME, provider)
        if key:
            return key
    except Exception:
        pass
    
    return _fallback_load_key(provider)

def delete_key(provider: str) -> None:
    """Delete an API key from the OS native keychain."""
    try:
        keyring.delete_password(SERVICE_NAME, provider)
    except Exception:
        _fallback_delete_key(provider)

def _fallback_save_key(provider: str, key: str) -> None:
    config_path = Path.home() / ".config" / "repopilot" / "keys"
    config_path.mkdir(parents=True, exist_ok=True)
    with open(config_path / provider, "w") as f:
        f.write(key)

def _fallback_load_key(provider: str) -> str | None:
    config_path = Path.home() / ".config" / "repopilot" / "keys" / provider
    if config_path.exists():
        with open(config_path, "r") as f:
            return f.read().strip()
    return None

def _fallback_delete_key(provider: str) -> None:
    config_path = Path.home() / ".config" / "repopilot" / "keys" / provider
    if config_path.exists():
        os.remove(config_path)
