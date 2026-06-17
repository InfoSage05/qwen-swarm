from app.sandbox.sandbox_client import SandboxClient
from app.sandbox.filesystem import SandboxFileSystem
from app.sandbox.models import SandboxResponse
from app.schemas.evidence import ExecutionResult

class SandboxExecutor:
    """High-level abstraction for agents and tools to execute code safely."""
    
    def __init__(self):
        self.client = SandboxClient()
        self.fs = SandboxFileSystem()
        self.ask_permission = None  # Callable[[str], Awaitable[bool]]
        
    async def run_command(self, command: str, args: list[str], cwd: str = ".", timeout: int = 30) -> ExecutionResult:
        """Executes a command and maps it to the ExecutionResult schema."""
        if self.ask_permission:
            full_cmd = f"{command} {' '.join(args)}"
            approved = await self.ask_permission(full_cmd)
            if not approved:
                return ExecutionResult(
                    status="failure",
                    stdout="",
                    stderr="User denied permission to run this command.",
                    return_code=-1,
                    execution_time_ms=0
                )
                
        resp: SandboxResponse = await self.client.execute(command, args, cwd, timeout)
        
        if resp.timeout_occurred:
            status = "timeout"
        elif resp.return_code == 0:
            status = "success"
        else:
            status = "failure"
            
        return ExecutionResult(
            status=status,
            stdout=resp.stdout,
            stderr=resp.stderr,
            return_code=resp.return_code,
            execution_time_ms=resp.execution_time_ms
        )
