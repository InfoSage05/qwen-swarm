from pydantic import BaseModel, Field
from typing import List, Optional

class FileNode(BaseModel):
    path: str
    language: str
    size: int
    line_count: int
    last_modified: float

class SymbolNode(BaseModel):
    symbol_name: str
    symbol_type: str
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    signature: Optional[str] = None

class DependencyEdge(BaseModel):
    source_file: str
    target_file: str
    relationship_type: str = "imports"

class CallEdge(BaseModel):
    caller_symbol: str
    callee_symbol: str
    relationship_type: str = "calls"

class RepositoryGraph(BaseModel):
    files: List[FileNode] = Field(default_factory=list)
    symbols: List[SymbolNode] = Field(default_factory=list)
    dependencies: List[DependencyEdge] = Field(default_factory=list)
    calls: List[CallEdge] = Field(default_factory=list)

class ModuleSummary(BaseModel):
    module_name: str
    summary: str

class FileSummary(BaseModel):
    file_path: str
    summary: str

class RepositorySummary(BaseModel):
    repository_summary: str
    module_summaries: List[ModuleSummary] = Field(default_factory=list)
    file_summaries: List[FileSummary] = Field(default_factory=list)
