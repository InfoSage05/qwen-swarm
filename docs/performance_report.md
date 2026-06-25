# Performance Dashboard

## Hackathon Metrics: Baseline vs RepoPilot

### Scenario: Repository Analysis
#### Latency (Lower is Better)
```text
Baseline  | █████ (11,200ms)
RepoPilot | █████ (10,650ms)
```
> **Latency Reduction: 550ms**

#### Token Efficiency
- **Cache Hit Rate:** 50.0%
- **Tokens Saved (Zero-Copy):** 12,000 tokens

### Scenario: Large Refactor
#### Latency (Lower is Better)
```text
Baseline  | ██████████████████████████████████████ (76,500ms)
RepoPilot | ████████████████████████████████████ (73,000ms)
```
> **Latency Reduction: 3,500ms**

#### Token Efficiency
- **Cache Hit Rate:** 83.3%
- **Tokens Saved (Zero-Copy):** 75,000 tokens

### Scenario: Feature Addition
#### Latency (Lower is Better)
```text
Baseline  | █████████████████ (34,700ms)
RepoPilot | ████████████████ (32,825ms)
```
> **Latency Reduction: 1,875ms**

#### Token Efficiency
- **Cache Hit Rate:** 75.0%
- **Tokens Saved (Zero-Copy):** 40,500 tokens

### Scenario: Repair Workflow
#### Latency (Lower is Better)
```text
Baseline  | ███████ (14,100ms)
RepoPilot | ██████ (12,800ms)
```
> **Latency Reduction: 1,300ms**

#### Token Efficiency
- **Cache Hit Rate:** 66.7%
- **Tokens Saved (Zero-Copy):** 28,000 tokens
