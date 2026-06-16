import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.inference.client import InferenceClient
from app.orchestration.orchestrator import SwarmOrchestrator
from app.schemas.evidence import ExecutionEvidence

@pytest.fixture
def mock_inference_client():
    client = MagicMock(spec=InferenceClient)
    client.chat = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_orchestrator_pipeline(mock_inference_client):
    plan_dict = {
        "tasks": [
            {"id": "t1", "title": "Test 1", "description": "Desc 1", "target_files": ["f1.py"], "priority": "medium", "dependencies": []},
            {"id": "t2", "title": "Test 2", "description": "Desc 2", "target_files": ["f2.py"], "priority": "medium", "dependencies": []}
        ]
    }
    
    executor_dict = {
        "task_id": "t1",
        "files_modified": ["f1.py"],
        "summary": "Did work",
        "diff_description": "Added line",
        "confidence": 0.9
    }
    
    review_dict = {
        "approved": True,
        "reason": "Looks good",
        "issues": [],
        "recommendations": []
    }
    
    repair_dict = {
        "failure_reason": "Test failure",
        "affected_files": ["tests/test_context.py"],
        "proposed_fix": "diff ...",
        "confidence": 0.95
    }
    
    def chat_side_effect(*args, **kwargs):
        name = kwargs.get("response_format", {}).get("json_schema", {}).get("name", "")
        if name == "Plan":
            return {"choices": [{"message": {"content": json.dumps(plan_dict)}}]}
        elif name == "ExecutorResult":
            return {"choices": [{"message": {"content": json.dumps(executor_dict)}}]}
        elif name == "ReviewDecision":
            return {"choices": [{"message": {"content": json.dumps(review_dict)}}]}
        elif name == "RepairPlan":
            return {"choices": [{"message": {"content": json.dumps(repair_dict)}}]}
        return {}

    async def chat_stream_side_effect(*args, **kwargs):
        name = kwargs.get("response_format", {}).get("json_schema", {}).get("name", "")
        if name == "Plan":
            yield json.dumps(plan_dict)
        elif name == "ExecutorResult":
            yield json.dumps(executor_dict)
        elif name == "ReviewDecision":
            yield json.dumps(review_dict)
        elif name == "RepairPlan":
            yield json.dumps(repair_dict)

    mock_inference_client.chat_stream = MagicMock(side_effect=chat_stream_side_effect)

    orchestrator = SwarmOrchestrator(context_payload="MOCK_CONTEXT", inference_client=mock_inference_client)
    
    events_received = []
    async def log_event(data): events_received.append("TASK_COMPLETED")
    orchestrator.event_bus.subscribe("TASK_COMPLETED", log_event)

    mock_evidence = ExecutionEvidence(
        files_modified=[],
        tests_run=2,
        tests_passed=2,
        tests_failed=0,
        mypy_passed=True,
        ruff_passed=True,
        stdout="All tests passed",
        stderr=""
    )

    with patch("app.orchestration.orchestrator.collect_evidence", new_callable=AsyncMock, return_value=mock_evidence):
        result = await orchestrator.receive_request("Do the task")

    assert result.approved is True
    assert "TASK_COMPLETED" in events_received
    # Either chat or chat_stream is called 4 times. Let's assert on chat_stream.call_count
    assert mock_inference_client.chat_stream.call_count == 4  # 1 planner + 2 executors + 1 reviewer

