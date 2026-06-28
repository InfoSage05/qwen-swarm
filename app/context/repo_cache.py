from pathlib import Path
from app.context.models import RepositoryGraph, RepositorySummary
import logging

logger = logging.getLogger(__name__)

class RepoCache:
    """Manages serialization of repository context to disk."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir).resolve()
        self.graph_dir = self.data_dir / "repo_graphs"
        self.summary_dir = self.data_dir / "summaries"
        
        # Ensure directories exist
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        
    def save_graph(self, graph: RepositoryGraph, name: str = "latest"):
        path = self.graph_dir / f"{name}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(graph.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to cache graph: {e}")

    def save_summary(self, summary: RepositorySummary, name: str = "latest"):
        path = self.summary_dir / f"{name}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(summary.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to cache summary: {e}")
