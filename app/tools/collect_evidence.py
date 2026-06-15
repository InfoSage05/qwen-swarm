from app.sandbox.executor import SandboxExecutor
from app.schemas.evidence import ExecutionEvidence
from app.tools.run_pytest import run_pytest
from app.tools.run_mypy import run_mypy
from app.tools.run_ruff import run_ruff

async def collect_evidence(target_dir: str, executor: SandboxExecutor) -> ExecutionEvidence:
    """Aggregates execution tools to produce ExecutionEvidence."""
    pytest_res = await run_pytest(target_dir, executor)
    mypy_res = await run_mypy(target_dir, executor)
    ruff_res = await run_ruff(target_dir, executor)
    
    return ExecutionEvidence(
        files_modified=[],  # Would use git_diff to populate this
        tests_run=pytest_res["passed"] + pytest_res["failed"],
        tests_passed=pytest_res["passed"],
        tests_failed=pytest_res["failed"],
        mypy_passed=mypy_res["passed"],
        ruff_passed=ruff_res["passed"],
        stdout=pytest_res["stdout"],
        stderr=pytest_res["stderr"]
    )
