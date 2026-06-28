import logging
from app.sandbox.executor import SandboxExecutor

logger = logging.getLogger(__name__)

async def git_diff(target_dir: str, executor: SandboxExecutor) -> dict:
    """Generates GitDiff structured output."""
    res = await executor.run_command("git", ["diff"], cwd=target_dir)
    return {
        "diff_summary": res.stdout,
        "files_changed": [],
        "insertions": 0,
        "deletions": 0
    }

async def git_branch(branch_name: str, target_dir: str, executor: SandboxExecutor) -> bool:
    """Creates and checks out a new branch."""
    res = await executor.run_command("git", ["checkout", "-b", branch_name], cwd=target_dir)
    if res.return_code == 0:
        logger.info(f"Successfully checked out new branch {branch_name}")
        return True
    logger.error(f"Failed to create branch {branch_name}: {res.stderr}")
    return False

async def git_commit_auto(target_dir: str, executor: SandboxExecutor, client=None) -> bool:
    """Generates a commit message using inference client and commits changes."""
    # First, stage all changes
    await executor.run_command("git", ["add", "."], cwd=target_dir)
    
    # Get diff
    diff_res = await executor.run_command("git", ["diff", "--cached"], cwd=target_dir)
    diff_text = diff_res.stdout.strip()
    
    if not diff_text:
        logger.info("No changes to commit.")
        return False
        
    commit_msg = "Auto-commit: Update files"
    if client:
        try:
            prompt = f"Write a concise conventional commit message for the following diff. Only return the commit message string, nothing else.\n\n{diff_text}"
            messages = [{"role": "user", "content": prompt}]
            response = await client.chat(messages, temperature=0.3)
            if response and "choices" in response and len(response["choices"]) > 0:
                msg = response["choices"][0]["message"]["content"].strip()
                if msg.startswith('"') and msg.endswith('"'):
                    msg = msg[1:-1]
                # Sometimes models output markdown code blocks
                if msg.startswith('```') and msg.endswith('```'):
                    msg = msg.split('\n', 1)[-1].rsplit('\n', 1)[0].strip()
                if msg:
                    commit_msg = msg
        except Exception as e:
            logger.warning(f"Failed to generate commit message: {e}")
            
    res = await executor.run_command("git", ["commit", "-m", commit_msg], cwd=target_dir)
    if res.return_code == 0:
        logger.info(f"Successfully committed: {commit_msg}")
        return True
    else:
        logger.error(f"Failed to commit: {res.stderr}")
        return False
