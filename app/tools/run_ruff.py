from app.sandbox.executor import SandboxExecutor

async def run_ruff(target_dir: str, executor: SandboxExecutor, files: list[str] = None) -> dict:
    """Runs ruff for linting."""
    args = ["check"] + files if files else ["check", "."]
    result = await executor.run_command("ruff", args, cwd=target_dir)
    return {
        "passed": result.return_code == 0,
        "errors": result.stdout if result.return_code != 0 else "",
        "warnings": ""
    }

