from app.sandbox.executor import SandboxExecutor

async def git_diff(target_dir: str, executor: SandboxExecutor) -> dict:
    """Generates GitDiff structured output."""
    res = await executor.run_command("git", ["diff"], cwd=target_dir)
    return {
        "diff_summary": res.stdout,
        "files_changed": [],
        "insertions": 0,
        "deletions": 0
    }
