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
├── Dockerfile                  # Backend container image (optional)
├── app/
│   ├── main.py                 # FastAPI entrypoint
│   ├── api/                    # HTTP API routers (v1)
│   ├── domain/                 # Business logic (some parts are stubs)
│   └── schemas/                # Pydantic models for API
├── wingman_edge_agents/        # Agents, prompts, LLM client wrappers
├── telegram/                   # Example Telegram bot integration (demo)
├── database/                   # DB bootstrap/init (placeholders)
└── README.md                   # This file
```

## Setup & Installation

### 1. Clone the repository
```sh
git clone <repo-url>
cd Wingman_Edge
```

### 2. Create and activate a virtual environment
```sh
python -m venv .venv
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install dependencies

There is no single, canonical `requirements.txt` in the repo root. You can install the common dependencies used in the project with:

```bash
python -m pip install --upgrade pip
pip install fastapi uvicorn langchain langchain-ollama langchain-core sqlalchemy psycopg2-binary python-telegram-bot ollama httpx pydantic pydantic-settings
```

Alternatively create a `requirements.txt` or use `pyproject.toml` and your preferred installer.

### 4. Start Ollama (local model runtime)

Install Ollama following the instructions at https://ollama.com/ and pull a model:

```bash
ollama pull llama3
ollama serve
```

Ollama typically listens at `http://localhost:11434`.

### 5. Run the backend server (development)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Database & Persistence

- The repository contains placeholders for database initialization and models, but the running code does not persist chats to Postgres today.
- A `docker-compose.yml` is present at the project root and can be used as a starting point to spin up Postgres; however the `database/initdb/` folder currently does not include active SQL for initializing `pgvector` or tables.

When you are ready to enable DB persistence, recommended steps:

- Add SQLAlchemy models and CRUD helpers.
- Add a small `init.sql` to `database/initdb/` to enable `pgvector` and create tables.
- Configure `DATABASE_URL` in `.env` and wire the connection in `app/main.py` or domain services.

## Key Dependencies

- **FastAPI**: Web API framework
- **Uvicorn**: ASGI server
- **LangChain / langchain-ollama / langchain-core**: Agent & prompt building and Ollama integration
- **Ollama**: Local model runtime (recommended to install locally)
- **SQLAlchemy**: Planned ORM for DB persistence (not yet wired)
- **python-telegram-bot**: Example Telegram integration

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

