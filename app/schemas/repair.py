from pydantic import BaseModel, Field, field_validator
from typing import List

class RepairPlan(BaseModel):
    failure_reason: str = Field(...)
    affected_files: List[str] = Field(...)
    proposed_fix: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator('confidence', mode='before')
    @classmethod
    def normalize_confidence(cls, v):
        if isinstance(v, str):
            v = v.replace('%', '').strip()
            try:
                v = float(v)
            except ValueError:
                pass
        if isinstance(v, (int, float)) and v > 1.0:
            return v / 100.0
        return v

