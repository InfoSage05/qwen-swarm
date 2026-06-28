import os
import hashlib
from pathlib import Path
from pydantic import BaseModel
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    chromadb = None
    SentenceTransformer = None

class ContextChunk(BaseModel):
    id: str
    content: str
    metadata: dict
    distance: float = 0.0

class ContextVectorStore:
    def __init__(self):
        if chromadb is None or SentenceTransformer is None:
            raise RuntimeError("chromadb and sentence-transformers are required for ContextVectorStore")
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = None
        self.collection = None

    def _get_cache_dir(self, repo_hash: str) -> str:
        cache_dir = Path.home() / ".cache" / "repopilot" / repo_hash
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir)

    def is_indexed(self, repo_hash: str) -> bool:
        cache_dir = self._get_cache_dir(repo_hash)
        db_file = os.path.join(cache_dir, "chroma.sqlite3")
        return os.path.exists(db_file)

    def _init_client(self, repo_hash: str):
        cache_dir = self._get_cache_dir(repo_hash)
        self.client = chromadb.PersistentClient(path=cache_dir)
        self.collection = self.client.get_or_create_collection(name="repo_context")

    def index(self, graph, repo_hash: str):
        self._init_client(repo_hash)
        
        ids = []
        documents = []
        metadatas = []
        
        # Index files
        if hasattr(graph, 'files'):
            for f in graph.files:
                file_path = getattr(f, 'path', str(f))
                ids.append(f"file_{file_path}")
                summary = getattr(f, 'summary', "")
                documents.append(f"File {file_path}: {summary}")
                metadatas.append({"type": "file", "path": file_path})
            
        # Index symbols
        if hasattr(graph, 'symbols'):
            for sym in graph.symbols:
                symbol_id = getattr(sym, 'symbol_name', getattr(sym, 'name', str(sym)))
                ids.append(f"symbol_{symbol_id}")
                doc = getattr(sym, 'docstring', "") or f"Symbol {symbol_id}"
                documents.append(f"Symbol {symbol_id}: {doc}")
                metadatas.append({"type": "symbol", "id": symbol_id})
            
        if not ids:
            return

        embeddings = self.model.encode(documents).tolist()
        
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.add(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

    def query(self, repo_hash: str, task: str, top_k: int = 20) -> list[ContextChunk]:
        if not self.collection:
            self._init_client(repo_hash)
            
        task_embedding = self.model.encode([task]).tolist()[0]
        results = self.collection.query(
            query_embeddings=[task_embedding],
            n_results=min(top_k, self.collection.count())
        )
        
        chunks = []
        if results and results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunks.append(ContextChunk(
                    id=results['ids'][0][i],
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    distance=results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                ))
        return chunks
