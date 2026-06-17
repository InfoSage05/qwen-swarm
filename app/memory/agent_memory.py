import os
import sqlite3
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class SwarmMemory:
    """SQLite-based agentic memory for storing context-specific experiences and patches."""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = workspace_path
        self.db_dir = os.path.join(self.workspace_path, ".repopilot")
        self.db_path = os.path.join(self.db_dir, "memory.db")
        self._init_db()

    def _init_db(self):
        """Initializes the database and creates required tables."""
        try:
            os.makedirs(self.db_dir, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS repair_experiences (
                        error_signature TEXT PRIMARY KEY,
                        proposed_fix TEXT,
                        files_affected TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            finally:
                conn.close()
            logger.info(f"SwarmMemory database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SwarmMemory database: {str(e)}")

    def record_repair(self, error_signature: str, proposed_fix: str, files_affected: List[str]):
        """Records a successful repair/patch experience."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO repair_experiences (error_signature, proposed_fix, files_affected)
                    VALUES (?, ?, ?)
                """, (error_signature, proposed_fix, json.dumps(files_affected)))
                conn.commit()
            finally:
                conn.close()
            logger.info(f"Recorded successful repair for error signature: '{error_signature}'")
        except Exception as e:
            logger.error(f"Failed to record repair experience: {str(e)}")

    def lookup_repair(self, error_signature: str) -> Optional[Dict[str, Any]]:
        """Looks up a previously successful repair/patch for the given error signature."""
        try:
            if not os.path.exists(self.db_path):
                return None
                
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT proposed_fix, files_affected FROM repair_experiences WHERE error_signature = ?",
                    (error_signature,)
                )
                row = cursor.fetchone()
                if row:
                    logger.info(f"Cache HIT in SwarmMemory for error signature: '{error_signature}'")
                    return {
                        "proposed_fix": row[0],
                        "files_affected": json.loads(row[1])
                    }
                else:
                    logger.info(f"Cache MISS in SwarmMemory for error signature: '{error_signature}'")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to lookup repair experience: {str(e)}")
            
        return None
