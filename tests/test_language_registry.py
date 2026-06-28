import pytest
from app.context.language_registry import LanguageRegistry

def test_language_registry_initialization():
    registry = LanguageRegistry()
    assert registry._grammars is not None

def test_language_registry_get_language():
    registry = LanguageRegistry()
    # Depending on what's installed, these might be None or a Language object,
    # but the method should execute without errors.
    py_lang = registry.get_language('.py')
    js_lang = registry.get_language('.js')
    
    # Check lowercase mapping
    PY_lang = registry.get_language('.PY')
    assert py_lang == PY_lang
