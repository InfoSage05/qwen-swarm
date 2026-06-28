import asyncio
import os
import sys
import tempfile
from rich.console import Console
from app.sandbox.base import BaseSandbox, SandboxResult

console = Console()

class SubprocessSandbox(BaseSandbox):
    def __init__(self):
        console.print("[bold yellow]⚠️ Running without Docker isolation. Install Docker for safe execution.[/bold yellow]")
        
    async def run_code(self, code: str, timeout: int = 30) -> SandboxResult:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
            
        try:
            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONUNBUFFERED": "1"
            }
            if os.name == "nt":
                env["Path"] = os.environ.get("Path", "")
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=os.path.dirname(temp_path)
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                return SandboxResult(
                    stdout=stdout_bytes.decode('utf-8', errors='replace'),
                    stderr=stderr_bytes.decode('utf-8', errors='replace'),
                    exit_code=process.returncode,
                    timed_out=False
                )
            except asyncio.TimeoutError:
                process.kill()
                stdout_bytes, stderr_bytes = await process.communicate()
                return SandboxResult(
                    stdout=stdout_bytes.decode('utf-8', errors='replace'),
                    stderr=stderr_bytes.decode('utf-8', errors='replace') + "\nExecution timed out.",
                    exit_code=-1,
                    timed_out=True
                )
        except Exception as e:
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=-2,
                timed_out=False
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
