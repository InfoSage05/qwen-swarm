import pytest
import asyncio
import tempfile
import os
from app.sandbox.executor import SandboxExecutor
from app.tools.execute_python import execute_python

@pytest.mark.asyncio
async def test_sandbox_execute_python():
    executor = SandboxExecutor()
    code = "print('Hello Sandbox')"
    
    result = await execute_python(code, executor)
    
    assert result.status == "success"
    assert "Hello Sandbox" in result.stdout
    assert result.return_code == 0

@pytest.mark.asyncio
async def test_sandbox_timeout():
    executor = SandboxExecutor()
    code = "import time\ntime.sleep(2)"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
        
    try:
        result = await executor.run_command("python", [temp_path], timeout=1)
        assert result.status == "timeout"
        assert result.return_code == -1
    finally:
        os.unlink(temp_path)
