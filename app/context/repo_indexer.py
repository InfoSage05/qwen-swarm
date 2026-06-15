import os
from pathlib import Path
from typing import List
from app.context.models import FileNode
import logging

logger = logging.getLogger(__name__)

class RepoIndexer:
    """Recursively scans the repository, filtering files and extracting metadata."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.ignore_dirs = {
            ".git", "venv", "myenv", "node_modules", "dist", "build", 
            ".cache", "__pycache__", "coverage", ".next", "target",
            ".pytest_cache", ".gemini", "data"
        }
        self.supported_extensions = {
            ".py": "Python", 
            ".ts": "TypeScript", 
            ".js": "JavaScript", 
            ".go": "Go"
        }

    def get_files(self) -> List[FileNode]:
        file_nodes = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith('.')]
            
            for file in files:
                path = Path(root) / file
                if path.suffix in self.supported_extensions:
                    try:
                        stat = path.stat()
                        # Count lines efficiently
                        with open(path, "rb") as f:
                            lines = sum(1 for _ in f)
                        
                        node = FileNode(
                            path=str(path.relative_to(self.root_dir).as_posix()),
                            language=self.supported_extensions[path.suffix],
                            size=stat.st_size,
                            line_count=lines,
                            last_modified=stat.st_mtime
                        )
                        file_nodes.append(node)
                    except Exception as e:
                        logger.warning(f"Failed to process file {path}: {e}")
                        
        return file_nodes
