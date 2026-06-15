from app.sandbox.executor import SandboxExecutor
import tempfile
import os

async def apply_patch(patch_content: str, target_dir: str, executor: SandboxExecutor) -> bool:
    """Safely apply generated code changes via patch."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
        f.write(patch_content)
        temp_path = f.name
        
    try:
        res = await executor.run_command("git", ["apply", temp_path], cwd=target_dir)
        return res.return_code == 0
    finally:
        os.unlink(temp_path)
