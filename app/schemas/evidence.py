from pydantic import BaseModel, Field
from typing import List

class ExecutionResult(BaseModel):
    status: str = Field(...)  # "success", "failure", "timeout"
    stdout: str = Field(...)
    stderr: str = Field(...)
    return_code: int = Field(...)
    execution_time_ms: int = Field(...)

class ExecutionEvidence(BaseModel):
    files_modified: List[str] = Field(default_factory=list)
    tests_run: int = Field(default=0)
    tests_passed: int = Field(default=0)
    tests_failed: int = Field(default=0)
    mypy_passed: bool = Field(default=False)
    ruff_passed: bool = Field(default=False)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
