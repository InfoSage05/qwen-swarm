import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from app.inference.client import InferenceClient
from app.orchestration.orchestrator import SwarmOrchestrator

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
    
    def chat_side_effect(*args, **kwargs):
        name = kwargs.get("response_format", {}).get("json_schema", {}).get("name", "")
        if name == "Plan":
            return {"choices": [{"message": {"content": json.dumps(plan_dict)}}]}
        elif name == "ExecutorResult":
            return {"choices": [{"message": {"content": json.dumps(executor_dict)}}]}
        elif name == "ReviewDecision":
            return {"choices": [{"message": {"content": json.dumps(review_dict)}}]}
        return {}

    async def chat_stream_side_effect(*args, **kwargs):
        name = kwargs.get("response_format", {}).get("json_schema", {}).get("name", "")
        if name == "Plan":
            yield json.dumps(plan_dict)
        elif name == "ExecutorResult":
            yield json.dumps(executor_dict)
        elif name == "ReviewDecision":
            yield json.dumps(review_dict)

    mock_inference_client.chat.side_effect = chat_side_effect
    mock_inference_client.chat_stream = chat_stream_side_effect

    orchestrator = SwarmOrchestrator(context_payload="MOCK_CONTEXT", inference_client=mock_inference_client)
    
    events_received = []
    async def log_event(data): events_received.append("TASK_COMPLETED")
    orchestrator.event_bus.subscribe("TASK_COMPLETED", log_event)

    result = await orchestrator.receive_request("Do the task")

    assert result.approved is True
    assert "TASK_COMPLETED" in events_received
    assert mock_inference_client.chat.call_count == 4  # 1 planner + 2 executors + 1 reviewer
