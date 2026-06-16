from pydantic import BaseModel, Field, field_validator
from typing import List

class ExecutorResult(BaseModel):
    task_id: str = Field(...)
    files_modified: List[str] = Field(...)
    summary: str = Field(...)
    diff_description: str = Field(...)
    proposed_patch: str = Field(default="", description="The unified diff/patch to apply to the workspace.")
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

