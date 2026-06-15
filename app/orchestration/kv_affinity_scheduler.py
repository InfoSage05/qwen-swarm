from typing import List, Dict
from pydantic import BaseModel
from app.schemas.planner import Task
import os

class TaskBatch(BaseModel):
    batch_id: str
    tasks: List[Task]
    repository_region: str

class KVCacheAffinityScheduler:
    """Groups tasks by common file paths to maximize KV-cache prefix hits."""
    
    def create_batches(self, tasks: List[Task]) -> List[TaskBatch]:
        """Groups tasks based on the common directory of their target files."""
        batches: Dict[str, List[Task]] = {}
        
        for task in tasks:
            region = "global"
            if task.target_files:
                dirs = [os.path.dirname(f) for f in task.target_files if f]
                if dirs:
                    parts = dirs[0].replace('\\\\', '/').split('/')
                    region = parts[0] if parts[0] else "root"
            
            if region not in batches:
                batches[region] = []
            batches[region].append(task)
            
        return [
            TaskBatch(batch_id=f"batch_{i}", tasks=t_list, repository_region=region)
            for i, (region, t_list) in enumerate(batches.items())
        ]
        
    def estimate_cache_affinity(self, batch: TaskBatch) -> float:
        """Estimates the percentage of cache reuse for a batch."""
        if not batch.tasks: return 0.0
        return min(0.95, 0.40 + (len(batch.tasks) * 0.15))
