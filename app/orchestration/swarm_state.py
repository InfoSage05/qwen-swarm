from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.planner import Plan, Task
from app.schemas.executor import ExecutorResult
from app.schemas.reviewer import ReviewDecision
from app.schemas.evidence import ExecutionEvidence
from app.schemas.failure import FailureReport

class SwarmState(BaseModel):
    """Immutable state tracking for the swarm workflow."""
    active_tasks: List[Task] = Field(default_factory=list)
    completed_tasks: List[Task] = Field(default_factory=list)
    failed_tasks: List[Task] = Field(default_factory=list)
    executor_results: List[ExecutorResult] = Field(default_factory=list)
    plan: Optional[Plan] = None
    review: Optional[ReviewDecision] = None
    
    # Phase 4 Additions
    evidence: Optional[ExecutionEvidence] = None
    failure_reports: List[FailureReport] = Field(default_factory=list)
    repair_attempts: int = 0
