from typing import List, Tuple
from app.schemas.planner import Task
from app.agents.executor_agent import ExecutorAgent

class TaskRouter:
    """Assigns planner tasks to executors."""
    
    def __init__(self, executors: List[ExecutorAgent]):
        self.executors = executors
        
    def assign_tasks(self, tasks: List[Task]) -> List[Tuple[ExecutorAgent, Task]]:
        """Round-robin assignment implementation."""
        assignments = []
        if not self.executors:
            return assignments
            
        for i, task in enumerate(tasks):
            executor = self.executors[i % len(self.executors)]
            assignments.append((executor, task))
            
        return assignments
