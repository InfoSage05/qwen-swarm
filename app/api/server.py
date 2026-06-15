from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="RepoPilot Inference Foundation API",
    description="Provides a single unified entry point to interact with SGLang/vLLM backends."
)

app.include_router(router)
