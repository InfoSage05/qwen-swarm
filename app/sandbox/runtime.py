import asyncio
import time
import os
from app.sandbox.models import SandboxRequest, SandboxResponse

class SandboxRuntime:
    """Provides async process isolation using asyncio.create_subprocess_exec."""
    
    async def execute(self, req: SandboxRequest) -> SandboxResponse:
        start_time = time.time()
        timeout_occurred = False
        
        try:
            # Never use os.system() or subprocess.run() in async paths!
            process = await asyncio.create_subprocess_exec(
                req.command,
                *req.args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=req.cwd,
                env={**os.environ, **req.env}
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=req.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                stdout_bytes, stderr_bytes = await process.communicate()
                timeout_occurred = True
                
            return_code = process.returncode if not timeout_occurred else -1
            
        except Exception as e:
            stdout_bytes, stderr_bytes = b"", str(e).encode()
            return_code = -2
            
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return SandboxResponse(
            stdout=stdout_bytes.decode(errors='replace'),
            stderr=stderr_bytes.decode(errors='replace'),
            return_code=return_code,
            execution_time_ms=execution_time_ms,
            timeout_occurred=timeout_occurred
        )
