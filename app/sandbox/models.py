from pydantic import BaseModel, Field
from typing import Dict

class SandboxRequest(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    cwd: str = Field(default=".")
    timeout: int = Field(default=30)
    env: Dict[str, str] = Field(default_factory=dict)

class SandboxResponse(BaseModel):
    stdout: str
    stderr: str
    return_code: int
    execution_time_ms: int
    timeout_occurred: bool = False
