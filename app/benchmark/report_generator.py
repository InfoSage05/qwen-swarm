import json
from app.schemas.benchmark import BenchmarkReport

class ReportGenerator:
    """Generates Markdown and JSON reports for Hackathon judging."""
    
    def generate_json(self, reports: list[BenchmarkReport], output_path: str):
        data = [r.model_dump() for r in reports]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
    def generate_markdown(self, reports: list[BenchmarkReport], output_path: str):
        lines = ["# Performance Dashboard\n"]
        lines.append("## Hackathon Metrics: Baseline vs RepoPilot\n")
        
        for rep in reports:
            lines.append(f"### Scenario: {rep.scenario}")
            
            # Scale blocks for readability
            scale = 2000 
            base_lat_blocks = max(1, int(rep.baseline_latency_ms / scale))
            repo_lat_blocks = max(1, int(rep.repopilot_latency_ms / scale))
            
            lines.append("#### Latency (Lower is Better)")
            lines.append("```text")
            lines.append(f"Baseline  | {'█' * base_lat_blocks} ({rep.baseline_latency_ms:,}ms)")
            lines.append(f"RepoPilot | {'█' * repo_lat_blocks} ({rep.repopilot_latency_ms:,}ms)")
            lines.append("```")
            lines.append(f"> **Latency Reduction: {rep.latency_improvement:,}ms**\n")
            
            lines.append("#### Token Efficiency")
            lines.append(f"- **Cache Hit Rate:** {rep.cache_hit_rate:.1f}%")
            lines.append(f"- **Tokens Saved (Zero-Copy):** {rep.token_savings:,} tokens\n")
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
