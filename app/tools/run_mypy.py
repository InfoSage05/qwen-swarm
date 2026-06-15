from app.sandbox.executor import SandboxExecutor

async def run_mypy(target_dir: str, executor: SandboxExecutor) -> dict:
    """Runs mypy for type checking."""
    result = await executor.run_command("mypy", [target_dir])
    return {
        "passed": result.return_code == 0,
        "errors": result.stdout if result.return_code != 0 else "",
        "warnings": ""
    }
