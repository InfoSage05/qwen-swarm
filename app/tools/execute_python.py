from app.sandbox.executor import SandboxExecutor
from app.schemas.evidence import ExecutionResult
import tempfile
import os

async def execute_python(code: str, executor: SandboxExecutor) -> ExecutionResult:
    """Runs arbitrary generated code inside the sandbox."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
        
    try:
        return await executor.run_command("python", [temp_path])
    finally:
        os.unlink(temp_path)
