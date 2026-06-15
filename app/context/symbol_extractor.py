from typing import List
from pathlib import Path
from app.context.models import SymbolNode
import logging

logger = logging.getLogger(__name__)

class SymbolExtractor:
    """Extracts functions, classes, and methods from a tree-sitter AST."""

    def extract(self, root_node, content: bytes, file_path: str) -> List[SymbolNode]:
        symbols = []
        if not root_node:
            return symbols
            
        def traverse(node):
            try:
                if node.type == 'function_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        sym = SymbolNode(
                            symbol_name=content[name_node.start_byte:name_node.end_byte].decode('utf-8'),
                            symbol_type='function',
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        )
                        symbols.append(sym)
                elif node.type == 'class_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        sym = SymbolNode(
                            symbol_name=content[name_node.start_byte:name_node.end_byte].decode('utf-8'),
                            symbol_type='class',
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        )
                        symbols.append(sym)
                
                for child in node.children:
                    traverse(child)
            except Exception as e:
                logger.warning(f"Failed to extract symbol in {file_path}: {e}")

        traverse(root_node)
        return symbols
