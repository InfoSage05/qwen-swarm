import os
import json
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from app.orchestration.swarm_state import SwarmState

SESSION_FILE = ".repopilot_session.json"

class SessionData(BaseModel):
    chat_history: List[Dict[str, str]]
    context_payload: str
    swarm_state: SwarmState

class SessionManager:
    """Manages persistence of the swarm workflow session."""
    
    @staticmethod
    def session_exists() -> bool:
        return os.path.exists(SESSION_FILE)
        
    @staticmethod
    def save_session(chat_history: List[Dict[str, str]], context_payload: str, swarm_state: SwarmState):
        data = SessionData(
            chat_history=chat_history,
            context_payload=context_payload,
            swarm_state=swarm_state
        )
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=2))
            
    @staticmethod
    def load_session() -> Optional[SessionData]:
        if not SessionManager.session_exists():
            return None
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                return SessionData.model_validate_json(content)
        except Exception as e:
            print(f"[SessionManager] Failed to load session: {e}")
            return None

    @staticmethod
    def clear_session():
        if SessionManager.session_exists():
            os.remove(SESSION_FILE)
