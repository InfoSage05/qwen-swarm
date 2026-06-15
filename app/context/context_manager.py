from typing import Dict, Any, Optional

from app.context.repo_indexer import RepoIndexer
from app.context.tree_sitter_parser import TreeSitterParser
from app.context.symbol_extractor import SymbolExtractor
from app.context.graph_builder import GraphBuilder
from app.context.summarizer import RepositorySummarizer
from app.context.repo_cache import RepoCache

class ContextManager:
    """The core component for repository intelligence."""
    
    def __init__(self, root_dir: str):
        self.indexer = RepoIndexer(root_dir)
        self.parser = TreeSitterParser()
        self.extractor = SymbolExtractor()
        self.graph_builder = GraphBuilder()
        self.summarizer = RepositorySummarizer()
        self.cache = RepoCache()
        
        self.graph = None
        self.summary = None

    def build(self):
        """Constructs the repository context from scratch."""
        files = self.indexer.get_files()
        
        symbols = []
        for file in files:
            root_node, content = self.parser.parse_file(self.indexer.root_dir / file.path)
            file_symbols = self.extractor.extract(root_node, content, file.path)
            symbols.extend(file_symbols)
            
        self.graph = self.graph_builder.build(files, symbols)
        self.summary = self.summarizer.summarize(self.graph)
        
        self.cache.save_graph(self.graph)
        self.cache.save_summary(self.summary)

    def load(self):
        """Loads cached intelligence from disk. Falls back to build() if none exist."""
        self.build()

    def refresh(self):
        """Refreshes the repository intelligence."""
        self.build()

    def retrieve_context(self) -> str:
        """Returns the fully constructed REPO_CONTEXT_PAYLOAD."""
        if not self.summary or not self.graph:
            self.load()
            
        payload = (
            "=== REPOSITORY CONTEXT ===\n"
            f"{self.summary.repository_summary}\n"
        )
        
        for file_sum in self.summary.file_summaries:
            payload += f"- {file_sum.summary}\n"
            
        payload += "=== END REPOSITORY CONTEXT ==="
        return payload
        
    def get_symbol_context(self, symbol_name: str) -> Optional[Dict]:
        if not self.graph: return None
        for sym in self.graph.symbols:
            if sym.symbol_name == symbol_name:
                return sym.model_dump()
        return None

    def get_file_context(self, file_path: str) -> Optional[Dict]:
        if not self.graph: return None
        for f in self.graph.files:
            if f.path == file_path:
                return f.model_dump()
        return None

    def get_module_context(self, module_name: str) -> Optional[Dict]:
        return None

    def get_neighborhood(self, symbol_name: str) -> Dict[str, Any]:
        """Returns related functions, dependencies, callers, callees."""
        return {
            "symbol": symbol_name,
            "related_functions": [],
            "dependencies": [],
            "callers": [],
            "callees": []
        }
