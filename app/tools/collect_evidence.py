from app.sandbox.executor import SandboxExecutor
from app.schemas.evidence import ExecutionEvidence
from app.tools.run_pytest import run_pytest
from app.tools.run_mypy import run_mypy
from app.tools.run_ruff import run_ruff

async def collect_evidence(target_dir: str, executor: SandboxExecutor) -> ExecutionEvidence:
    """Aggregates execution tools to produce ExecutionEvidence."""
    # Find modified/added python files using git status
    res = await executor.run_command("git", ["status", "--porcelain"], cwd=target_dir)
    modified_files = []
    if res.return_code == 0:
        for line in res.stdout.splitlines():
            # git status --porcelain outputs 'XY filepath'
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                status, path = parts
                if path.endswith(".py") and ("M" in status or "?" in status or "A" in status):
                    modified_files.append(path)

    # Run pytest on target_dir
    pytest_res = await run_pytest(target_dir, executor)
    
    # Run mypy and ruff only on modified files if any exist
    if modified_files:
        mypy_res = await run_mypy(target_dir, executor, modified_files)
        ruff_res = await run_ruff(target_dir, executor, modified_files)
    else:
        # Default to pass if no files were modified
        mypy_res = {"passed": True, "errors": "", "warnings": ""}
        ruff_res = {"passed": True, "errors": "", "warnings": ""}
    
    return ExecutionEvidence(
        files_modified=modified_files,
        tests_run=pytest_res["passed"] + pytest_res["failed"],
        tests_passed=pytest_res["passed"],
        tests_failed=pytest_res["failed"],
        mypy_passed=mypy_res["passed"],
        ruff_passed=ruff_res["passed"],
        stdout=pytest_res["stdout"],
        stderr=pytest_res["stderr"]
    )

