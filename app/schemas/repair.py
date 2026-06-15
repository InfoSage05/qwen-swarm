from pydantic import BaseModel, Field
from typing import List

class RepairPlan(BaseModel):
    failure_reason: str = Field(...)
    affected_files: List[str] = Field(...)
    proposed_fix: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
