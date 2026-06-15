from pydantic import BaseModel, Field
from typing import List

class ReviewDecision(BaseModel):
    approved: bool = Field(...)
    reason: str = Field(...)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
