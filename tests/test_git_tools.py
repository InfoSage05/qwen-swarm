import pytest
from unittest.mock import AsyncMock
from app.tools.git import git_diff, git_branch
from app.sandbox.executor import SandboxExecutor

@pytest.mark.asyncio
async def test_git_diff():
    executor = AsyncMock(spec=SandboxExecutor)
    executor.run_command.return_value = AsyncMock(stdout="diff content")
    result = await git_diff(".", executor)
    assert result["diff_summary"] == "diff content"
    executor.run_command.assert_called_once_with("git", ["diff"], cwd=".")

@pytest.mark.asyncio
async def test_git_branch():
    executor = AsyncMock(spec=SandboxExecutor)
    executor.run_command.return_value = AsyncMock(return_code=0)
    result = await git_branch("new_feature", ".", executor)
    assert result is True
    executor.run_command.assert_called_once_with("git", ["checkout", "-b", "new_feature"], cwd=".")
