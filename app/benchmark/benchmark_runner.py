from app.schemas.benchmark import BenchmarkScenarioResult, BenchmarkReport
from app.schemas.metrics import LatencyMetric, TokenMetric, CacheMetric, ThroughputMetric
from app.benchmark.benchmark_scenarios import scenarios

class BenchmarkRunner:
    """Runs simulations of execution to generate comparative metrics."""
    
    async def run_scenario(self, scenario: dict, mode: str) -> BenchmarkScenarioResult:
        tasks = scenario["simulated_tasks"]
        base_tokens = scenario["base_prompt_tokens"]
        comp_tokens = scenario["completion_tokens_per_task"]
        
        if mode == "Baseline":
            total_prompt_tokens = base_tokens * tasks
            cached_tokens = 0
            ttft_ms = int((base_tokens / 10000) * 500)
            total_latency_ms = (ttft_ms * tasks) + (comp_tokens * tasks * 10)
            cache_hits = 0
            cache_misses = tasks
            
        else: # RepoPilot Zero-Copy
            total_prompt_tokens = base_tokens + (base_tokens * (tasks - 1))
            cached_tokens = base_tokens * (tasks - 1)
            first_ttft_ms = int((base_tokens / 10000) * 500)
            warm_ttft_ms = 50
            
            ttft_ms = int((first_ttft_ms + (warm_ttft_ms * (tasks - 1))) / max(1, tasks))
            total_latency_ms = first_ttft_ms + (warm_ttft_ms * (tasks - 1)) + (comp_tokens * tasks * 10)
            cache_hits = max(0, tasks - 1)
            cache_misses = 1

        total_comp = comp_tokens * tasks
        throughput_tpm = (tasks / (total_latency_ms / 60000)) if total_latency_ms > 0 else 0
        
        return BenchmarkScenarioResult(
            scenario_name=scenario["name"],
            mode=mode,
            latency=LatencyMetric(ttft_ms=ttft_ms, total_latency_ms=total_latency_ms),
            tokens=TokenMetric(
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_comp,
                total_tokens=total_prompt_tokens + total_comp,
                cached_tokens=cached_tokens,
                saved_tokens=cached_tokens
            ),
            cache=CacheMetric(
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                prefix_reuse=cache_hits / tasks if tasks > 0 else 0.0,
                agent_reuse=0.9
            ),
            throughput=ThroughputMetric(
                tasks_completed=tasks,
                tasks_per_minute=round(throughput_tpm, 2),
                average_task_duration_ms=int(total_latency_ms / tasks) if tasks > 0 else 0
            )
        )
        
    async def compare_modes(self, scenario: dict) -> BenchmarkReport:
        baseline = await self.run_scenario(scenario, "Baseline")
        repopilot = await self.run_scenario(scenario, "RepoPilot")
        
        return BenchmarkReport(
            scenario=scenario["name"],
            baseline_latency_ms=baseline.latency.total_latency_ms,
            repopilot_latency_ms=repopilot.latency.total_latency_ms,
            latency_improvement=baseline.latency.total_latency_ms - repopilot.latency.total_latency_ms,
            token_savings=repopilot.tokens.saved_tokens,
            cache_hit_rate=repopilot.cache.prefix_reuse * 100
        )
        
    async def run_all(self) -> list[BenchmarkReport]:
        reports = []
        for s in scenarios:
            rep = await self.compare_modes(s)
            reports.append(rep)
        return reports
