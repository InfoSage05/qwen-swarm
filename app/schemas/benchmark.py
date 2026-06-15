from pydantic import BaseModel
from app.schemas.metrics import LatencyMetric, TokenMetric, CacheMetric, ThroughputMetric

class BenchmarkScenarioResult(BaseModel):
    scenario_name: str
    mode: str
    latency: LatencyMetric
    tokens: TokenMetric
    cache: CacheMetric
    throughput: ThroughputMetric

class BenchmarkReport(BaseModel):
    scenario: str
    baseline_latency_ms: int
    repopilot_latency_ms: int
    latency_improvement: int
    token_savings: int
    cache_hit_rate: float
