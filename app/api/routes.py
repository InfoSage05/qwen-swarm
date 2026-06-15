from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.inference.client import InferenceClient

router = APIRouter()
client = InferenceClient()

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]

@router.get("/health")
async def health_check():
    """Verify backend availability."""
    return await client.health_check()

@router.get("/model")
async def get_model_info():
    """Retrieve info on loaded model."""
    return await client.model_info()

@router.post("/chat")
async def chat(request: ChatRequest):
    """Forward request through InferenceClient."""
    return await client.chat(messages=request.messages)
