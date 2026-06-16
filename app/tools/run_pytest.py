from app.sandbox.executor import SandboxExecutor

async def run_pytest(target_dir: str, executor: SandboxExecutor) -> dict:
    """Runs pytest and extracts test results."""
    result = await executor.run_command("python", ["-m", "pytest", "-v"], cwd=target_dir)
    
    passed = result.stdout.count("PASSED")
    failed = result.stdout.count("FAILED")
    
    return {
        "passed": passed,
        "failed": failed,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "status": "success" if result.return_code == 0 else "failure"
    }
