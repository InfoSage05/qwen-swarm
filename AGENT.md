# AGENT.md

# QwenSwarm: RepoPilot

## Master Architecture Specification & Agent Constitution

Version: 1.0

Status: Authoritative Source of Truth

---

# Purpose

This document is the governing specification for the QwenSwarm: RepoPilot codebase.

All future implementation decisions, code generation tasks, architectural choices, and agent behaviors MUST follow the rules defined in this document.

If another prompt conflicts with this document, this document takes precedence.

The goal of RepoPilot is to build a Zero-Copy Multi-Agent Software Engineering System that can autonomously understand, modify, test, review, and repair large software repositories while minimizing repeated context processing through shared KV-cache utilization.

---

# Project Vision

RepoPilot is not a chatbot.

RepoPilot is not a generic agent framework.

RepoPilot is an autonomous software engineering system.

The system should function similarly to an AI software engineering team composed of specialized agents:

* Planner Agent
* Executor Agents
* Reviewer Agent
* Repair Agent

All agents operate on a shared repository understanding that is loaded once and reused through SGLang prefix caching and RadixAttention.

The core innovation is treating repository understanding as a persistent GPU-resident memory resource.

---

# Core Problem

Modern coding agents repeatedly reprocess large repository context.

Typical workflow:

Repository Context
→ Agent Call
→ Repository Context
→ Agent Call
→ Repository Context
→ Agent Call

This creates:

* High latency
* High token usage
* High compute cost
* Redundant inference work

Large repositories frequently contain:

* 15,000–30,000 tokens
* hundreds of files
* thousands of symbols

RepoPilot eliminates repeated processing by loading repository context once and sharing it across agent workflows.

---

# Architectural Thesis

Repository understanding should be amortized across the entire swarm.

Instead of:

Repository Context × N Agent Calls

We want:

Repository Context × 1

Then:

New Tokens × N Agent Calls

The repository becomes a shared memory substrate.

The swarm performs work on top of that memory.

---

# Design Principles

## Principle 1

Shared Context First

All agents must share the same repository context.

No agent may construct its own repository understanding.

The Context Manager is the only source of repository state.

---

## Principle 2

Structured Outputs Only

All agent outputs must be schema constrained.

Use:

* Pydantic v2
* JSON schemas
* SGLang XGrammar

Do not use:

* regex parsing
* string extraction
* brittle text post-processing

---

## Principle 3

Agent Specialization

Each agent owns a single responsibility.

Planner:
Creates plans.

Executor:
Modifies code.

Reviewer:
Evaluates outputs.

Repair:
Fixes failures.

Do not merge responsibilities.

---

## Principle 4

Asynchronous Execution

The entire swarm must be built around asyncio.

Concurrency should be achieved through:

asyncio.gather()

Do not introduce synchronous bottlenecks.

---

## Principle 5

Evidence-Based Validation

Code changes must be validated through execution.

No agent may claim success without evidence.

Evidence includes:

* test output
* lint output
* type-check output
* execution results

---

# Technology Stack

## Runtime

Python 3.11+

---

## Inference

Primary:

SGLang

Secondary:

vLLM compatibility layer

---

## Foundation Model

Default:

Qwen/Qwen2.5-7B-Instruct

Architecture must support model replacement.

Future models should require minimal changes.

---

## Infrastructure

Modal

GPU Target:

A10G

---

## Structured Outputs

Pydantic v2

JSON Schema

OpenAI-compatible response_format

XGrammar

---

## Repository Analysis

tree-sitter

ast

networkx

---

## Testing

pytest

ruff

mypy

---

# Forbidden Technologies

The following frameworks are prohibited:

* LangChain
* CrewAI
* AutoGen
* LlamaIndex

Reason:

RepoPilot requires custom orchestration optimized for KV-cache reuse.

Generic frameworks introduce abstraction layers that do not understand cache affinity.

---

# Repository Architecture

Required repository layout:

qwenswarm-repopilot/

README.md

AGENT.md

prompts/

app/

tests/

docs/

data/

Implementation must follow this structure.

Do not invent alternative layouts.

---

# System Components

## Context Layer

Responsible for repository understanding.

Components:

* Repository Indexer
* Tree-Sitter Parser
* Symbol Extractor
* Graph Builder
* Context Manager

Responsibilities:

* parse repository
* build symbol graph
* build dependency graph
* build call graph
* generate repository summaries

Output:

REPO_CONTEXT

---

## Inference Layer

Responsible for communication with language models.

Components:

* Backend Interface
* SGLang Backend
* vLLM Backend

Purpose:

Allow future backend replacement without changing agent logic.

---

## Agent Layer

Contains all swarm agents.

Required agents:

PlannerAgent

ExecutorAgent

ReviewerAgent

RepairAgent

Each agent must inherit from:

BaseAgent

---

## Orchestration Layer

Coordinates the swarm.

Components:

* Orchestrator
* Scheduler
* Event Bus
* Swarm State

Responsibilities:

* task routing
* parallel execution
* lifecycle management
* state tracking

---

## Sandbox Layer

Responsible for safe code execution.

Components:

* Sandbox Runtime
* Sandbox Server
* Sandbox Client
* Execution Environment

Responsibilities:

* execute generated code
* run tests
* collect evidence
* isolate execution

---

## Benchmark Layer

Responsible for performance evaluation.

Metrics:

* TTFT
* Total latency
* Cache hit rate
* Token usage
* Throughput

---

# Zero-Copy KV Cache Architecture

All agent requests must begin with the identical shared prefix.

Required structure:

System Prompt

Repository Context

Agent Task

The repository context must be stable.

The prefix must remain identical whenever possible.

This maximizes RadixAttention cache reuse.

---

# Repository Context Format

The Context Manager should construct:

Repository Summary

File Summaries

Symbol Graph

Dependency Graph

Call Graph

Documentation Context

The result becomes:

REPO_CONTEXT_PAYLOAD

This payload is shared across all agents.

---

# Planner Agent

Responsibilities:

* analyze user request
* identify impacted modules
* generate execution plan
* divide work into tasks

Planner never edits files.

Planner never executes code.

Planner only plans.

---

# Executor Agent

Responsibilities:

* modify source code
* generate patches
* implement features
* update tests

Executor never approves its own work.

Executor must produce evidence.

---

# Reviewer Agent

Responsibilities:

* validate implementations
* inspect diffs
* analyze evidence
* approve or reject changes

Reviewer must remain independent.

---

# Repair Agent

Responsibilities:

* analyze failures
* generate fixes
* retry execution

Maximum retries:

3

After exceeding retries:

Return failure report.

---

# Sandbox Requirements

The sandbox is a required component.

The sandbox must support:

execute_python

run_pytest

run_mypy

run_ruff

apply_patch

collect_stdout

collect_stderr

Sandbox results must be returned as structured schemas.

---

# Evidence Requirements

All modifications must generate:

ExecutionEvidence

Required fields:

* files_modified
* tests_run
* tests_passed
* tests_failed
* stdout
* stderr

Reviewer consumes evidence.

Reviewer never consumes raw claims.

---

# Future Optimization Targets

The following features are explicitly planned:

Semantic Code Graph

Self-Healing Loops

Speculative Executors

Consensus Review

KV-Affinity Scheduling

Dynamic Batching

Repository Memory Compression

These features should be implemented incrementally.

---

# Success Criteria

RepoPilot is considered successful when it can:

1. Parse a repository.

2. Construct repository context.

3. Load context into SGLang.

4. Create a task plan.

5. Execute modifications.

6. Run validation.

7. Repair failures.

8. Produce verified patches.

9. Demonstrate lower latency through cache reuse.

10. Benchmark performance against a non-cached baseline.

---

# Final Directive

Always optimize for:

Repository Understanding

Cache Reuse

Structured Outputs

Autonomous Validation

Low Latency

Do not optimize for framework complexity.

Do not optimize for prompt engineering tricks.

The innovation of RepoPilot is architectural.

All implementation decisions must reinforce the Zero-Copy Multi-Agent vision.
