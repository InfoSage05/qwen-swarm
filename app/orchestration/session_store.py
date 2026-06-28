import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.orchestration.swarm_state import SwarmState

class SessionMeta(BaseModel):
    id: str
    repo_path: str
    created_at: str
    updated_at: str

class SessionData(BaseModel):
    id: str
    repo_path: str
    chat_history: list
    swarm_state: SwarmState
    context_hash: str

class SessionStore:
    def __init__(self):
        self.db_dir = Path.home() / ".local" / "share" / "repopilot"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "sessions.db"
        self._init_db()
        
    def _get_connection(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            version = cursor.fetchone()[0]
            
            if version == 0:
                cursor.execute("""
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY,
                        repo_path TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        schema_version INTEGER DEFAULT 1,
                        chat_history_json TEXT,
                        swarm_state_json TEXT,
                        context_hash TEXT
                    )
                """)
                cursor.execute("PRAGMA user_version = 1")
                conn.commit()
                
    def save(self, session_id: str, repo_path: str, chat_history: list, swarm_state: SwarmState, context_hash: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            exists = cursor.fetchone()
            
            now = datetime.utcnow().isoformat()
            
            if exists:
                cursor.execute("""
                    UPDATE sessions
                    SET updated_at = ?,
                        chat_history_json = ?,
                        swarm_state_json = ?,
                        context_hash = ?
                    WHERE id = ?
                """, (
                    now,
                    json.dumps(chat_history),
                    swarm_state.model_dump_json(),
                    context_hash,
                    session_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO sessions (id, repo_path, created_at, updated_at, schema_version, chat_history_json, swarm_state_json, context_hash)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """, (
                    session_id,
                    repo_path,
                    now,
                    now,
                    json.dumps(chat_history),
                    swarm_state.model_dump_json(),
                    context_hash
                ))
            conn.commit()
            
    def load(self, session_id: str) -> Optional[SessionData]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT repo_path, chat_history_json, swarm_state_json, context_hash FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
                
            return SessionData(
                id=session_id,
                repo_path=row[0],
                chat_history=json.loads(row[1]),
                swarm_state=SwarmState.model_validate_json(row[2]),
                context_hash=row[3]
            )
            
    def list_sessions(self, repo_path: str) -> List[SessionMeta]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, created_at, updated_at FROM sessions WHERE repo_path = ? ORDER BY updated_at DESC", (repo_path,))
            rows = cursor.fetchall()
            return [SessionMeta(id=r[0], repo_path=repo_path, created_at=r[1], updated_at=r[2]) for r in rows]
            
    def delete(self, session_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
