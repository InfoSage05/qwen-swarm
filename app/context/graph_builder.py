from typing import List
from app.context.models import FileNode, SymbolNode, DependencyEdge, CallEdge, RepositoryGraph

class GraphBuilder:
    """Builds semantic relationships between repository elements."""
    
    def build(self, files: List[FileNode], symbols: List[SymbolNode]) -> RepositoryGraph:
        """
        Construct the RepositoryGraph combining files, symbols, dependencies, and calls.
        Currently sets up the schemas. AST-based dependency extraction is stubbed.
        """
        graph = RepositoryGraph()
        graph.files = files
        graph.symbols = symbols
        
        # Future: Use tree-sitter queries to find imports and calls here.
        # Stubbing for Phase 2 integration testing:
        if len(files) >= 2:
            graph.dependencies.append(DependencyEdge(
                source_file=files[0].path,
                target_file=files[1].path
            ))
            
        if len(symbols) >= 2:
            graph.calls.append(CallEdge(
                caller_symbol=symbols[0].symbol_name,
                callee_symbol=symbols[1].symbol_name
            ))
            
        return graph
