# Benchmark Philosophy

The benchmark system inside RepoPilot strictly focuses on empirical performance characteristics inherent to the Zero-Copy context architecture.

## Core Goal
Prove that **Zero-Copy Repository Context** > **Repeated Repository Processing**

## Required Metrics
- **TTFT (Time To First Token)**: Measures inference latency.
- **TotalLatency**: Request start to completion.
- **TokenUsage**: Prompt vs Completion tokens.
- **CacheHitRate**: Percentage of requests served using cached prefixes.
- **AgentThroughput**: Tasks completed per minute.

## Benchmark Modes
- **Mode 1: Baseline**: Every request rebuilds the context natively.
- **Mode 2: RepoPilot**: Shared repository context cached once.

We use simulated metrics in the default setup to demonstrate the mathematical advantages prior to deploying heavily on Modal.
