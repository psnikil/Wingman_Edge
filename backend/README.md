## Wingman Backend (FastAPI + Ollama)

Welcome to the backend of the Wingman Edge agent. This backend provides a compact FastAPI service that talks to local LLMs (via Ollama) and exposes two agent endpoints today: a chat agent and a web-search/summarization agent. Persistent DB storage (Postgres + pgvector) is planned but not yet wired into the running code — the repo contains placeholders and compose orchestration to help bootstrap DB later.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture Structure](#architecture-structure)
- [Setup & Installation](#setup--installation)
- [Database & Persistence](#database--persistence)
- [Key Dependencies](#key-dependencies)
- [Ollama LLM Integration](#ollama-llm-integration)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Extending & Contributing](#extending--contributing)
- [Future Roadmap](#future-roadmap)

## Project Overview

The backend powers a small, local agent service intended to run on edge devices (for example a Raspberry Pi). Current capabilities:

- Chat agent: conversation flows through LangChain + Ollama via `wingman_edge_agents`.
- Web agent: fetch-and-summarize web content (simple agent implementation).
- Ollama utilities: helpers to check, start and list Ollama models.

Planned/coming soon:

- Postgres + pgvector persistence for embeddings and RAG workflows. (Placeholders exist under `database/` and a `docker-compose.yml` at project root; DB wiring into the Python app is not completed.)

## Architecture Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI entrypoint
│   ├── api/                    # HTTP API routers (v1)
│   ├── domain/                 # Business logic
│   └── schemas/                # Pydantic models for API
├── wingman_edge_agents/        # Agents, prompts, LLM client wrappers
├── database/                   # DB bootstrap/init (Placeholders)
└── README.md                   # This file
```

## Setup & Installation

The project uses `uv` for dependency management and execution.

### 1. Clone the repository
```sh
git clone <repo-url>
cd Wingman_Edge
```

### 2. Install dependencies (using uv)

```bash
uv sync
```

### 3. Start Ollama (local model runtime)

Install Ollama following the instructions at https://ollama.com/ and pull a model:

```bash
ollama pull qwen3.5:2b
ollama serve
```

Ollama typically listens at `http://localhost:11434`.

### 4. Run the backend server (development)

From the project root:

```bash
uv run python -m backend.main
```

The API will be available at `http://localhost:8000`.

## Database & Persistence

> [!NOTE]
> **TODO: Database Implementation**
> - Implement SQLAlchemy models in `backend/database`.
> - Add CRUD helpers for chat history and agent state.
> - Configure `DATABASE_URL` and initialize the connection in the FastAPI app.
> - Add Alembic for database migrations.

- The repository contains placeholders for database initialization and models, but the running code does not persist data to Postgres today.
- A `docker-compose.yml` is present at the project root and can be used to spin up a Postgres instance with `pgvector` support.

## Key Dependencies

- **uv**: Dependency management and execution
- **FastAPI**: Web API framework
- **LangChain / langchain-ollama / langchain-core**: Agent & prompt building
- **Ollama**: Local model runtime
- **SQLAlchemy**: Planned ORM for DB persistence

## Ollama LLM Integration

- Utilities to check & list models: `backend/wingman_edge_agents/utils/ollama_client.py` (functions like `is_ollama_running`, `start_ollama`, `list_ollama_models`).
- LangChain LLM client wrapper: `backend/wingman_edge_agents/services/edge_llm_client/llm_client.py` which provides `LLMClient` and supports Ollama, OpenAI and Anthropic (falls back to Ollama by default).
- Ensure `ollama serve` is running and at least one model is pulled (for example `ollama pull llama3`).

## API Reference

The FastAPI app mounts a small set of routers. Routes are registered from `backend/app/api/v1/` and are available at the root path.

| Route                  | Method | Purpose |
|------------------------|--------|---------|
| `/`                    | GET    | Root health/welcome message |
| `/list_ollama_models`  | GET    | Return list of models available to Ollama |
| `/is_init`             | GET    | Initialization helper — will try to start/list Ollama and report status |
| `/chat`                | POST   | Chat agent endpoint — accepts `model`, `query` (and optional `context`) |
| `/web_agent`           | POST   | Web agent endpoint — accepts `model`, `query`, and optional `context` |

Example `POST /chat` payload (JSON):

```json
{
  "model": "qwen3.5:2b",
  "query": "Hello, what's a good recipe for chickpea curry?"
}
```

Example `POST /web_agent` payload:

```json
{
  "model": "qwen3.5:2b",
  "query": "Summarize the latest news on renewable energy",
  "context": "Optional context or prior conversation"
}
```

Notes:
- The request/response Pydantic models live in `backend/app/schemas/chat.py`. Some handlers in `app/api/v1/` expect fields named `model` and `query`.

## Testing

There are no automated tests bundled currently. For a quick smoke test, run the server locally and call the endpoints using `curl` or an HTTP client.

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Then test a simple endpoint:

```bash
curl http://localhost:8000/
curl http://localhost:8000/list_ollama_models
```

## Extending & Contributing

Suggested next work items:

- Wire DB persistence: implement SQLAlchemy models and enable `DATABASE_URL` configuration in the app.
- Add `requirements.txt` or make `pyproject.toml` the single source of dependencies.
- Add tests and CI for the key endpoints.
- Improve request validation to align router handlers with Pydantic schemas.

When contributing, keep agents modular and place new tools under `wingman_edge_agents/tools/`.

## Future Roadmap

- Add Postgres + pgvector persistence and RAG workflows
- Add Alembic migrations and DB seeding scripts
- Improve Telegram bot integration and add authentication
- Add WebSocket-based streaming responses for real-time chat

---

If you'd like, I can:

- add a minimal `requirements.txt` and `.env.example` for the backend,
- wire a simple DB connection using `DATABASE_URL` and add a small example table,
- or make the Dockerfile multi-arch / Pi-friendly for arm64 builds.

Ask which of the above you'd like me to implement next and I will proceed.

