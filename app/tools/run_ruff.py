from app.sandbox.executor import SandboxExecutor

async def run_ruff(target_dir: str, executor: SandboxExecutor) -> dict:
    """Runs ruff for linting."""
    result = await executor.run_command("ruff", ["check", "."], cwd=target_dir)
    return {
        "passed": result.return_code == 0,
        "errors": result.stdout if result.return_code != 0 else "",
        "warnings": ""
    }
