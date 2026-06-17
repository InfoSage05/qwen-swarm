import os
import shutil
import tempfile
import pytest
from app.memory.agent_memory import SwarmMemory
from app.orchestration.orchestrator import SwarmOrchestrator

@pytest.fixture
def temp_workspace():
    # Set up a temporary directory to act as a workspace
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Tear down the temporary directory
    shutil.rmtree(temp_dir)

def test_swarm_memory_initialization(temp_workspace):
    memory = SwarmMemory(workspace_path=temp_workspace)
    assert os.path.exists(memory.db_dir)
    assert os.path.exists(memory.db_path)

def test_swarm_memory_record_and_lookup(temp_workspace):
    memory = SwarmMemory(workspace_path=temp_workspace)
    
    error_sig = "pytest_failed_assertion_in_test_hello_py"
    proposed_fix = "diff --git a/hello.py b/hello.py\n..."
    files = ["hello.py"]
    
    # Verify cache miss initially
    assert memory.lookup_repair(error_sig) is None
    
    # Record the repair
    memory.record_repair(error_sig, proposed_fix, files)
    
    # Verify cache hit and data matching
    cached = memory.lookup_repair(error_sig)
    assert cached is not None
    assert cached["proposed_fix"] == proposed_fix
    assert cached["files_affected"] == files

def test_error_signature_generation():
    # Instantiate SwarmOrchestrator to test helper method (we can mock client)
    from unittest.mock import MagicMock
    client = MagicMock()
    orchestrator = SwarmOrchestrator(context_payload="MOCK", inference_client=client)
    
    stdout = "Traceback (most recent call last):\n  File \"e:\\Hackathons\\Qwen Cloud Global Hackathon\\app\\hello.py\", line 12, in main\n    print(y)\nNameError: name 'y' is not defined"
    stderr = ""
    
    sig1 = orchestrator._generate_error_signature("linter", stdout, stderr)
    
    # Different absolute path, same relative structure and line numbers (which should be stripped)
    stdout_diff_path = "Traceback (most recent call last):\n  File \"/home/user/workspace/app/hello.py\", line 42, in main\n    print(y)\nNameError: name 'y' is not defined"
    
    sig2 = orchestrator._generate_error_signature("linter", stdout_diff_path, stderr)
    
    # The signature should be identical because it normalizes paths and line numbers!
    assert sig1 == sig2
