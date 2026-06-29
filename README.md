# QwenSwarm: RepoPilot

**Zero-Copy Multi-Agent Software Engineering System**
*Built for the Qwen Cloud Global AI Hackathon (Agent Society Track)*

RepoPilot is an autonomous, repository-scale software engineering assistant designed to understand, modify, validate, and repair large codebases using a swarm of specialized AI agents.

Unlike traditional coding agents that repeatedly reload repository context on every interaction, RepoPilot introduces a **Zero-Copy KV-Cache Architecture** powered by SGLang RadixAttention. The repository is parsed once, transformed into a structured repository context, loaded into GPU memory, and reused across all agent interactions. This dramatically reduces:
- Latency (time-to-first-token)
- Repeated computation / token waste
- Repository reprocessing overhead

---

## 🚀 Quick Start & Installation

You can install and run RepoPilot globally on any repository using `npm`.

### 1. Global Installation

Install RepoPilot globally using `npm` (works in WSL, cmd, powershell, macOS, and Linux):

```bash
npm install -g repo-pilot
```

Alternatively, you can run it directly without installing it globally using `npx`:

```bash
npx repo-pilot
```

### 2. Configuration Setup

Before running RepoPilot, you need to configure your LLM backend api keys. In the root of the project/repository you want RepoPilot to analyze, create a `.env` file:

```bash
# Initialize a template .env file
# (RepoPilot will automatically do this for you on first run if it's missing)
```

Fill in the credentials in your `.env` file:

```env
# 1. DashScope (Qwen Cloud Services) - [Recommended Backend]
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 2. Modal endpoint - [SGLang / vLLM Serverless Backend]
MODAL_ENDPOINT_URL=https://your-modal-app-name.modal.run/v1

# 3. OpenAI / Custom vLLM - [Alternative Local Backend]
OPENAI_API_KEY=your_openai_api_key_here
# OPENAI_BASE_URL=http://localhost:8000/v1

# 4. Zhipu AI / GLM Backend
GLM_API_KEY=your_glm_api_key_here
GLM_ENDPOINT_URL=https://api.z.ai/api/coding/paas/v4

# 5. Multi-Modal Vision Model Integration via OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Engine configurations
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
BACKEND_TYPE=dashscope

# Optional: Local Ollama backend
# OLLAMA_HOST=http://localhost:11434

# 6. Web Search Integration (Tavily)
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. Usage

To launch RepoPilot and start an interactive swarm session in any workspace, simply navigate to that repository in your terminal and run:

```bash
repopilot
```
*(or `repo-pilot`)*

RepoPilot will:
1. Scan and build a **Repository Context Graph** (ignoring cache, venv, and build directories) across multiple languages using Tree-sitter.
2. Index context blocks via ChromaDB (Vector RAG) for lightning-fast retrieval.
3. Prompt you to select your preferred inference backend, including local Ollama models.
4. Spin up the specialized Agent Swarm to discuss the codebase or work on tasks.
5. Save your session history to a local SQLite database (`~/.local/share/repopilot/sessions.db`) for seamless continuation later using `/sessions`.

---

## 🛠️ Architecture & Core Components

RepoPilot operates as a swarm of task-specific, highly integrated agents:

```
                  ┌────────────────────────┐
                  │      User Request      │
                  │   (Text / Image URL)   │
                  └───────────┬────────────┘
                              ▼
                  ┌────────────────────────┐
                  │    Conductor Agent     │
                  │ (Dynamic Orchestrator) │
                  └───────────┬────────────┘
                              │ generates subtasks
                              ▼
                  ┌────────────────────────┐
                  │ Dynamic Worker Agents  │
                  │ (Code/Vision Subtasks) │
                  └───────────┬────────────┘
                              │ proposes patch
                              ▼
                  ┌────────────────────────┐
            ┌──── │   Sandbox Execution    │ ────► [Tests Pass] ──► Patch
            │     │  (Pytest, Mypy, Ruff)  │
            │     └───────────┬────────────┘
            │                 │
            │           [Tests Fail]
            │                 │
            │                 ▼
            │     ┌────────────────────────┐
            └─────┤      Repair Agent      │
   [Self-Healing] │ (Generates Fix Patch)  │
                  └────────────────────────┘
```

1. **Repository Intelligence Layer (Vector RAG):** Uses multi-language `tree-sitter`, abstract syntax trees (ASTs), and `ChromaDB` to index codebases. It extracts a semantic graph containing summaries, symbols, call graphs, import networks, and documentation context.
2. **Conductor Agent (Dynamic Orchestrator):** Analyzes user requests and dynamically generates a bespoke agentic workflow consisting of specialized subtasks, selected models, and context-sharing access lists. 
3. **Dynamic Worker Agents:** Execute the highly tailored subtasks generated by the Conductor, ranging from planning and code implementation to architectural review. They are capable of utilizing tools such as Git commands for diffing and committing automatically.
4. **Docker Sandbox Execution Layer:** A dedicated, isolated environment (Docker containers by default) that executes code, runs tests (`pytest`), lints (`ruff`), and performs static analysis (`mypy`) to automatically validate the generated patches without affecting your host machine.
5. **Self-Healing Loop (Repair Agent):** Analyzes compiler/sandbox errors and attempts to fix broken implementations iteratively. Includes advanced heuristics to prevent infinite error loops by increasing temperature or backing off when repeated errors occur.
6. **Tool Integration:** Integrated tools like **Web Search** (`tavily-python` API) enable agents to dynamically fetch the latest external information or documentation reliably. Git integration provides branching and automatic commit capabilities.

---

## 🚀 Usage

Once running, the interactive console supports:
- `/plan <task> [--image <url>]`: Generate and review an execution plan.
- `/execute`: Execute the previously generated plan.
- `/agent <task> [--image <url>]`: Fully autonomous execution.
- `/pr <url>`: Run the Release Assistant.

**Note on Multi-Modal / Vision Support:**
If you want the swarm to analyze UI screenshots or architectural diagrams, set `OPENROUTER_API_KEY=sk-or-v1-...` in your `.env` file. You can then append `--image <url>` to your `/agent` or `/plan` commands, and the Conductor will dynamically route the image analysis to a specialized Vision Node (defaulting to `qwen-2-vl-7b-instruct:free`).

---

## 💻 Tech Stack

- **Infrastructure:** [Modal](https://modal.com/) (A10G GPU / H100 serverless hosting) or local execution.
- **Inference Engines:** [SGLang](https://github.com/sgl-project/sglang), [vLLM](https://github.com/vllm-project/vllm), [DashScope](https://help.aliyun.com/zh/dashscope/), or **Ollama** for robust local usage.
- **Base Models:** `Qwen/Qwen2.5-Coder-32B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`
- **Context Parsing:** Multi-language `tree-sitter` (Python, JS, TS, Java, Go, Rust), `ChromaDB` for Vector RAG, `sentence-transformers`
- **Session Persistence:** `SQLite`
- **Validation:** `pytest`, `mypy`, `ruff` inside secure `Docker` sandboxes
- **Output Structuring:** `pydantic` v2, JSON Schema, SGLang XGrammar logit masking
