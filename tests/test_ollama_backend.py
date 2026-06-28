import pytest
from unittest.mock import AsyncMock, patch
from app.inference.ollama_backend import OllamaBackend

@pytest.mark.asyncio
@patch('app.inference.ollama_backend.ollama.AsyncClient')
async def test_ollama_backend_chat(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.chat = AsyncMock(return_value={"message": {"content": "Test response"}})
    
    backend = OllamaBackend()
    messages = [{"role": "user", "content": "Hello"}]
    
    response = await backend.chat(messages)
    assert response["choices"][0]["message"]["content"] == "Test response"
    mock_client.chat.assert_called_once()

@pytest.mark.asyncio
@patch('app.inference.ollama_backend.ollama.AsyncClient')
async def test_ollama_backend_health_check(mock_client_cls):
    mock_client = mock_client_cls.return_value
    mock_client.list = AsyncMock(return_value={"models": []})
    
    backend = OllamaBackend()
    result = await backend.health_check()
    assert result["status"] == "ok"
    assert result["backend"] == "ollama"
