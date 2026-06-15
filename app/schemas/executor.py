from pydantic import BaseModel, Field
from typing import List

class ExecutorResult(BaseModel):
    task_id: str = Field(...)
    files_modified: List[str] = Field(...)
    summary: str = Field(...)
    diff_description: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
