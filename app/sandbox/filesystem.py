import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager

class SandboxFileSystem:
    """Manages isolated filesystem operations for the sandbox."""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            self.base_dir = Path(tempfile.gettempdir()) / "repopilot_sandbox"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
            
    @contextmanager
    def create_isolated_workspace(self, source_repo: str):
        """Creates a temporary isolated copy of the repository for safe execution."""
        temp_dir = tempfile.mkdtemp(dir=self.base_dir)
        try:
            # Copy contents excluding heavy ignored dirs for speed
            shutil.copytree(
                source_repo, 
                temp_dir, 
                dirs_exist_ok=True, 
                ignore=shutil.ignore_patterns(".git", "venv", "myenv", "node_modules", ".cache", "__pycache__")
            )
            yield temp_dir
        finally:
            # Clean up all temporary resources
            shutil.rmtree(temp_dir, ignore_errors=True)
