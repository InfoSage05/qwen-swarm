from app.sandbox.executor import SandboxExecutor

async def run_mypy(target_dir: str, executor: SandboxExecutor, files: list[str] = None) -> dict:
    """Runs mypy for type checking."""
    args = files if files else ["."]
    result = await executor.run_command("mypy", args, cwd=target_dir)
    return {
        "passed": result.return_code == 0,
        "errors": result.stdout if result.return_code != 0 else "",
        "warnings": ""
    }

