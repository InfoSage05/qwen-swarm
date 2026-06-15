from pydantic import BaseModel, Field

class LatencyMetric(BaseModel):
    ttft_ms: int = Field(description="Time To First Token in milliseconds")
    total_latency_ms: int = Field(description="Request start to completion in milliseconds")

class TokenMetric(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    saved_tokens: int = 0

class CacheMetric(BaseModel):
    cache_hits: int = 0
    cache_misses: int = 0
    prefix_reuse: float = 0.0
    agent_reuse: float = 0.0

class ThroughputMetric(BaseModel):
    tasks_completed: int
    tasks_per_minute: float
    average_task_duration_ms: int
