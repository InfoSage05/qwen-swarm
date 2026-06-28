from app.context.models import RepositorySummary, FileSummary, RepositoryGraph

class RepositorySummarizer:
    """Generates concise summaries of the repository context to avoid brute-force dumping."""
    
    def summarize(self, graph: RepositoryGraph) -> RepositorySummary:
        """Generates File, Module, and Repository summaries."""
        file_summaries = []
        for f in graph.files:
            sym_count = len([s for s in graph.symbols if s.file_path == f.path])
            file_summaries.append(FileSummary(
                file_path=f.path,
                summary=f"{f.path} ({f.language}): {f.line_count} lines, {sym_count} symbols."
            ))
            
        repo_summary = f"Repository summary: {len(graph.files)} files, {len(graph.symbols)} symbols total."
        
        return RepositorySummary(
            repository_summary=repo_summary,
            module_summaries=[],
            file_summaries=file_summaries
        )
