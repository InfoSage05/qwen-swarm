from pydantic import BaseModel, Field
from typing import Optional

class FailureReport(BaseModel):
    tool: str = Field(...) # e.g., "pytest", "mypy", "ruff", "python"
    file: Optional[str] = Field(None)
    line: Optional[int] = Field(None)
    error_type: str = Field(...)
    message: str = Field(...)
