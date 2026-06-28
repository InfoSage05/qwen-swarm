import os
import hashlib
import warnings
from typing import Dict, Any, Optional

from app.context.repo_indexer import RepoIndexer
from app.context.tree_sitter_parser import TreeSitterParser
from app.context.symbol_extractor import SymbolExtractor
from app.context.graph_builder import GraphBuilder
from app.context.summarizer import RepositorySummarizer
from app.context.repo_cache import RepoCache
from app.context.vector_store import ContextVectorStore

def deprecated(reason):
    def decorator(func):
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__} is deprecated: {reason}", category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

class ContextManager:
    """The core component for repository intelligence."""
    
    def __init__(self, root_dir: str):
        self.indexer = RepoIndexer(root_dir)
        self.parser = TreeSitterParser()
        self.extractor = SymbolExtractor()
        self.graph_builder = GraphBuilder()
        self.summarizer = RepositorySummarizer()
        self.cache = RepoCache(os.path.join(root_dir, ".repopilot"))
        self.vector_store = ContextVectorStore()
        
        self.graph = None
        self.summary = None
        self.external_context = []
        self.repo_hash = hashlib.md5(os.path.abspath(root_dir).encode()).hexdigest()

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
        
        if not self.vector_store.is_indexed(self.repo_hash):
            self.vector_store.index(self.graph, self.repo_hash)

    def load(self):
        """Loads cached intelligence from disk. Falls back to build() if none exist."""
        self.build()

    def refresh(self):
        self.build()

    def refresh_incremental(self):
        if not self.graph or not self.summary:
            self.build()
            return
            
        try:
            import subprocess
            result = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=self.indexer.root_dir)
            if not result.stdout.strip():
                return
                
            changed_filepaths = []
            for line in result.stdout.split('\n'):
                if len(line) > 3:
                    changed_filepaths.append(line[3:].strip())
                    
            files = self.indexer.get_files()
            new_symbols = [sym for sym in self.graph.symbols if sym.file_path not in changed_filepaths]
            
            for file in files:
                if file.path in changed_filepaths:
                    root_node, content = self.parser.parse_file(self.indexer.root_dir / file.path)
                    file_symbols = self.extractor.extract(root_node, content, file.path)
                    new_symbols.extend(file_symbols)
                    
            self.graph = self.graph_builder.build(files, new_symbols)
            self.summary = self.summarizer.summarize(self.graph)
            
            self.cache.save_graph(self.graph)
            self.cache.save_summary(self.summary)
            
            # Re-index if incrementally updated
            self.vector_store.index(self.graph, self.repo_hash)
            
        except Exception:
            self.build()

    def retrieve_for_task(self, task: str) -> str:
        if not self.summary or not self.graph:
            self.load()
            
        chunks = self.vector_store.query(self.repo_hash, task, top_k=20)
        
        payload = f"=== RELEVANT CONTEXT FOR TASK: {task} ===\n\n"
        for idx, chunk in enumerate(chunks):
            payload += f"--- Result {idx+1} (Score: {chunk.distance:.2f}) ---\n"
            payload += f"{chunk.content}\n\n"
            
        if self.external_context:
            payload += "\n=== EXTERNAL CONTEXT (Web & URLs) ===\n"
            for ext in self.external_context:
                payload += f"--- Source: {ext['source']} ---\n{ext['content']}\n\n"
                
        payload += "=== END RELEVANT CONTEXT ===\n"
        return payload

    @deprecated("Use retrieve_for_task() for large repos")
    def retrieve_context(self) -> str:
        if not self.summary or not self.graph:
            self.load()
            
        git_status = ""
        try:
            import subprocess
            res = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=self.indexer.root_dir)
            if res.stdout.strip():
                git_status = "=== GIT STATUS (Unstaged/Dirty Files) ===\n" + res.stdout + "\n"
        except Exception:
            pass
            
        payload = (
            "=== REPOSITORY CONTEXT ===\n"
            f"{self.summary.repository_summary}\n"
        )
        
        for file_sum in self.summary.file_summaries:
            payload += f"- {file_sum.summary}\n"
            
        if self.external_context:
            payload += "\n=== EXTERNAL CONTEXT (Web & URLs) ===\n"
            for ext in self.external_context:
                payload += f"--- Source: {ext['source']} ---\n{ext['content']}\n\n"
            
        payload += "=== END REPOSITORY CONTEXT ===\n\n" + git_status
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
        return {
            "symbol": symbol_name,
            "related_functions": [],
            "dependencies": [],
            "callers": [],
            "callees": []
        }

    def add_external_context(self, source_name: str, content: str):
        self.external_context.append({
            "source": source_name,
            "content": content
        })
