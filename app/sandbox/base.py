from pydantic import BaseModel

class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool

class BaseSandbox:
    async def run_code(self, code: str, timeout: int = 30) -> SandboxResult:
        raise NotImplementedError
