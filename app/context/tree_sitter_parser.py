from pathlib import Path
from tree_sitter import Parser
import logging
from app.context.language_registry import LanguageRegistry

logger = logging.getLogger(__name__)

class TreeSitterParser:
    """Parses source code into syntax trees using Tree-sitter for multiple languages."""
    
    def __init__(self):
        self.registry = LanguageRegistry()
        self.parsers = {}

    def parse_file(self, file_path: Path):
        """Parse a file based on its extension and return AST root and raw bytes."""
        ext = file_path.suffix.lower()
        language = self.registry.get_language(ext)
        if not language:
            try:
                # Plain text fallback
                content = file_path.read_bytes()
                return None, content
            except Exception:
                return None, b""
                
        if ext not in self.parsers:
            parser = Parser(language)
            self.parsers[ext] = parser
            
        parser = self.parsers[ext]
        try:
            content = file_path.read_bytes()
            tree = parser.parse(content)
            return tree.root_node, content
        except Exception as e:
            logger.warning(f"Parser failed for {file_path}: {e}")
            return None, b""
