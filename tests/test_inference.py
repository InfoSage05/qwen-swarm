import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.api.server import app
from app.inference.client import InferenceClient

client = TestClient(app)

def test_config_loading():
    assert settings.BACKEND_TYPE in ["sglang", "vllm", "dashscope"]
    assert settings.GPU_TYPE == "a10g"

def test_backend_initialization():
    inf_client = InferenceClient()
    assert inf_client.backend is not None
    assert inf_client.backend.__class__.__name__.lower().startswith(settings.BACKEND_TYPE)

def test_health_route():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_model_info_route():
    response = client.get("/model")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == settings.MODEL_NAME
    assert data["backend"] == settings.BACKEND_TYPE
