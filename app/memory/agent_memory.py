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
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        preference_text TEXT UNIQUE,
                        last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                        access_count INTEGER DEFAULT 1
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

    def record_preference(self, preference_text: str):
        """Records a user preference."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO user_preferences (preference_text, last_accessed, access_count)
                    VALUES (?, CURRENT_TIMESTAMP, 1)
                    ON CONFLICT(preference_text) DO UPDATE SET
                        last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                """, (preference_text,))
                conn.commit()
            finally:
                conn.close()
            logger.info(f"Recorded user preference: '{preference_text}'")
        except Exception as e:
            logger.error(f"Failed to record user preference: {str(e)}")

    def lookup_preferences(self, limit: int = 5) -> List[str]:
        """Looks up the most relevant user preferences based on access count and recency."""
        try:
            if not os.path.exists(self.db_path):
                return []
                
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                # Sort by highest access count and then most recently accessed
                cursor.execute("""
                    SELECT preference_text FROM user_preferences 
                    ORDER BY access_count DESC, last_accessed DESC 
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                if rows:
                    # Update last_accessed for the retrieved items
                    for row in rows:
                        cursor.execute("""
                            UPDATE user_preferences SET 
                            last_accessed = CURRENT_TIMESTAMP,
                            access_count = access_count + 1
                            WHERE preference_text = ?
                        """, (row[0],))
                    conn.commit()
                    return [row[0] for row in rows]
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to lookup user preferences: {str(e)}")
            
        return []

    def prune_outdated_memory(self, days_old: int = 30):
        """Prunes outdated repair experiences and preferences."""
        try:
            if not os.path.exists(self.db_path):
                return
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM repair_experiences 
                    WHERE timestamp < datetime('now', ?)
                """, (f'-{days_old} days',))
                deleted_repairs = cursor.rowcount
                
                cursor.execute("""
                    DELETE FROM user_preferences 
                    WHERE last_accessed < datetime('now', ?) AND access_count < 5
                """, (f'-{days_old} days',))
                deleted_prefs = cursor.rowcount
                
                conn.commit()
                if deleted_repairs > 0 or deleted_prefs > 0:
                    logger.info(f"Pruned {deleted_repairs} outdated repairs and {deleted_prefs} outdated preferences.")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to prune outdated memory: {str(e)}")
