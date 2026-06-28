from tree_sitter import Language
import logging

logger = logging.getLogger(__name__)

class LanguageRegistry:
    def __init__(self):
        self._grammars = {}
        self._load_grammars()

    def _load_grammars(self):
        try:
            import tree_sitter_python as tspython
            self._grammars['.py'] = Language(tspython.language())
        except ImportError: pass
        
        try:
            import tree_sitter_javascript as tsjs
            self._grammars['.js'] = Language(tsjs.language())
            self._grammars['.jsx'] = Language(tsjs.language())
        except ImportError: pass

        try:
            import tree_sitter_typescript as tsts
            self._grammars['.ts'] = Language(tsts.language_typescript())
            self._grammars['.tsx'] = Language(tsts.language_tsx())
        except ImportError: pass

        try:
            import tree_sitter_java as tsjava
            self._grammars['.java'] = Language(tsjava.language())
        except ImportError: pass
        
        try:
            import tree_sitter_go as tsgo
            self._grammars['.go'] = Language(tsgo.language())
        except ImportError: pass
        
        try:
            import tree_sitter_rust as tsrust
            self._grammars['.rs'] = Language(tsrust.language())
        except ImportError: pass

    def get_language(self, extension: str) -> Language | None:
        return self._grammars.get(extension.lower())
