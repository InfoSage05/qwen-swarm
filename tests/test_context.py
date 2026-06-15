import pytest
import tempfile
from pathlib import Path
from app.context.context_manager import ContextManager

@pytest.fixture
def mock_repo():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        
        # Create a Python file
        py_file = root / "main.py"
        py_file.write_text("def hello_world():\n    return 'Hello'\n\nclass MyService:\n    def do_work(self):\n        pass\n")
        
        # Create an ignored directory and file
        venv = root / "venv"
        venv.mkdir()
        (venv / "ignored.py").write_text("def hidden(): pass")
        
        yield str(root)

def test_context_manager_build(mock_repo):
    cm = ContextManager(mock_repo)
    cm.build()
    
    # Assert indexer ignored venv
    assert len(cm.graph.files) == 1
    assert cm.graph.files[0].path == "main.py"
    
    # Assert symbols were extracted
    assert len(cm.graph.symbols) >= 3 # hello_world, MyService, MyService.do_work
    
    symbol_names = [s.symbol_name for s in cm.graph.symbols]
    assert "hello_world" in symbol_names
    assert "MyService" in symbol_names
    assert "MyService.do_work" in symbol_names

def test_context_manager_retrieve(mock_repo):
    cm = ContextManager(mock_repo)
    payload = cm.retrieve_context()
    
    assert "=== REPOSITORY CONTEXT ===" in payload
    assert "main.py (Python)" in payload
