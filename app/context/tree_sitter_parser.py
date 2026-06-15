from pathlib import Path
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
import logging

logger = logging.getLogger(__name__)

class TreeSitterParser:
    """Parses source code into syntax trees using Tree-sitter."""
    
    def __init__(self):
        try:
            self.PY_LANGUAGE = Language(tspython.language())
            self.parser = Parser(self.PY_LANGUAGE)
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter: {e}")
            self.parser = None

    def parse_file(self, file_path: Path):
        """Parse a Python file and return the Tree-sitter AST root node and raw bytes."""
        if not self.parser:
            return None, b""
            
        try:
            content = file_path.read_bytes()
            tree = self.parser.parse(content)
            return tree.root_node, content
        except Exception as e:
            logger.warning(f"Parser failed for {file_path}: {e}")
            return None, b""
