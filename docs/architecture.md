# RepoPilot Architecture

RepoPilot is designed around a multi-agent framework that orchestrates specialized agents to interact with, modify, and repair software repositories.

## Core Components

### 1. Context Engine (RAG)
The repository context engine is responsible for parsing your codebase into a semantic structure.
- **Multi-Language Tree-Sitter**: Supports Python, JS, TS, Java, Go, and Rust. It extracts abstract syntax trees to identify symbols (functions, classes) and generate call graphs.
- **Vector Store (ChromaDB)**: Extracts from the parsed AST are embedded using `sentence-transformers` and indexed into a local `ChromaDB` store. This enables rapid, relevance-based retrieval of code snippets directly applicable to the agent's current task.

### 2. Sandbox Isolation
RepoPilot performs execution and evaluation in an isolated environment.
- **Docker Sandbox**: The default strategy relies on Docker to build a container matching your project configuration. The system patches the container to evaluate code changes securely without destroying local environments.
- **Subprocess Sandbox**: As a fallback, executes changes directly using standard subprocess operations if Docker is unavailable.

### 3. Agent Swarm
- **Conductor Agent**: Responsible for interpreting user input and constructing a Directed Acyclic Graph (DAG) of necessary subtasks. The Conductor defines which models, context, and capabilities each worker needs.
- **Worker Agent**: Dynamic agents equipped with tools to modify code. Tools include Git primitives (`git_diff`, `git_branch`, `git_commit_auto`) and web search. Worker Agents can execute tasks in parallel for disjoint codebase elements.
- **Repair Agent**: Evaluates errors arising from test executions inside the sandbox. Uses an iterative self-healing loop equipped with back-off mechanisms and dynamic model temperature adjustments to prevent redundant correction cycles.

### 4. Orchestration & Persistence
- **Wave-Based Orchestrator**: Executes tasks grouped into waves based on the DAG dependencies. Utilizes an asynchronous `FileLockRegistry` to ensure concurrent modifications safely serialize file system writes.
- **SQLite Persistence**: Chat histories and dynamic state flows are saved locally via `session_store.py` providing resumable sessions through a simple CLI (`/sessions`).

### 5. LLM Inference Abstraction
- The system dynamically toggles between various backend inference providers including: SGLang, vLLM, DashScope, OpenRouter (for Multi-Modal Vision), and **Ollama** for seamless on-device local execution.

---

## TUI (Terminal User Interface)
Built utilizing the `rich` library. Features an interactive terminal dashboard mapping tasks, active thought processing (including live syntax highlighting for streaming diffs), and live process outputs.
