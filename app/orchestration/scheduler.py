import asyncio
from typing import List, Tuple
from app.schemas.executor import ExecutorResult
from app.agents.executor_agent import ExecutorAgent
from app.schemas.planner import Task

class Scheduler:
    """Manages concurrent execution of assigned tasks."""
    
    async def run_executors(self, context_payload: str, assignments: List[Tuple[ExecutorAgent, Task]]) -> List[ExecutorResult]:
        """Launches executors in parallel using asyncio.gather()."""
        
        async def run_single(executor: ExecutorAgent, task: Task) -> ExecutorResult:
            return await executor.execute_task(context_payload, task)
            
        tasks = [run_single(executor, task) for executor, task in assignments]
        
        # Parallel execution is mandatory
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid results, logging exceptions would go here
        valid_results = [res for res in results if isinstance(res, ExecutorResult)]
        return valid_results
