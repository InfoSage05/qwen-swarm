from typing import List
from app.context.models import SymbolNode
import logging

logger = logging.getLogger(__name__)

class SymbolExtractor:
    """Extracts functions, classes, and methods from a tree-sitter AST."""

    def extract(self, root_node, content: bytes, file_path: str) -> List[SymbolNode]:
        symbols = []
        if not root_node:
            return symbols
            
        def traverse(node, parent_class: str = None):
            try:
                current_parent = parent_class
                is_func = 'function' in node.type or 'method' in node.type
                is_class = 'class' in node.type or 'interface' in node.type or 'trait' in node.type

                if is_func:
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        func_name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        symbol_name = f"{parent_class}.{func_name}" if parent_class else func_name
                        sym = SymbolNode(
                            symbol_name=symbol_name,
                            symbol_type='function',
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        )
                        symbols.append(sym)
                elif is_class:
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        class_name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        sym = SymbolNode(
                            symbol_name=class_name,
                            symbol_type='class',
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1
                        )
                        symbols.append(sym)
                        current_parent = class_name
                
                for child in node.children:
                    traverse(child, current_parent)
            except Exception as e:
                logger.warning(f"Failed to extract symbol in {file_path}: {e}")

        traverse(root_node)
        return symbols
