import asyncio
import os
from typing import Dict

class FileLockRegistry:
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        
    async def get_lock(self, filepath: str) -> asyncio.Lock:
        abs_path = os.path.abspath(filepath)
        async with self._global_lock:
            if abs_path not in self._locks:
                self._locks[abs_path] = asyncio.Lock()
            return self._locks[abs_path]

file_locks = FileLockRegistry()
