# Wingman: Local LLM Chat App (Edge / Raspberry Pi)

Wingman is a lightweight, local agent backend designed to run on edge devices (for example a Raspberry Pi). It exposes a FastAPI backend that serves two primary endpoints today: a chat endpoint (driven by LangChain and Ollama) and a web-search endpoint (simple web agent). The backend can be interfaced via a Telegram bot, or any frontend through the HTTP API.

---

## Features

- **Local LLM chat**: Interact with local models via Ollama and LangChain
- **Web search agent**: Agent that can fetch and summarize web content
- **FastAPI backend**: Modular, production-friendly API
- **Telegram bot interface**: Lightweight bot to interact with the agent from Telegram
- **Planned DB support**: Postgres + vector extension (pgvector) for embeddings and search (not yet provisioned)
- **Containerized**: `Dockerfile` and `docker-compose.yml` included to run backend and initialize DB locally

---

## Project Structure

```
Wingman_Edge/
├── backend/    # FastAPI backend, API routes, services, and agent code
├── telegram/   # Telegram bot implementation and entrypoint
├── database/   # DB initialization scripts for docker-compose (Postgres + pgvector)
├── wingman_edge_agents/ # Agents, prompts, tools
├── README.md   # This file (global docs)
```

See subfolders for implementation details; parts of the codebase are still in-progress (DB integration, persistence).

---

## Quick Start (local, development)

### 1. Prerequisites

- **Python 3.13+** (project `pyproject.toml` requires >=3.13)
- **uv** (recommended for dependency management: https://docs.astral.sh/uv/)
- **Ollama** installed and running locally if you want to use local LLMs (https://ollama.com/)

Note: this project targets small, local setups such as Raspberry Pi. Ensure your Pi has sufficient disk, RAM and the proper Ollama/LLM runtime (or use a remote Ollama endpoint).

### 2. Run backend locally (using uv)

```bash
# Run the FastAPI server:
uv run python -m backend.main
# API available at: http://localhost:8000
```

### 3. Run Telegram bot locally (using uv)

```bash
# Run the telegram bot entrypoint:
uv run python telegram/main.py
```

---

## Docker (recommended for quick setup & DB init)

This repository includes a `Dockerfile` and a `docker-compose.yml` at the project root. `docker-compose` launches:
- `db` (Postgres) with an init SQL that enables `pgvector` and creates a minimal table to hold embeddings.
- `backend` (FastAPI + Ollama) built from `Dockerfile`.

Environment values are configurable via an `.env` file or by overriding environment variables in the compose command.

Example `docker-compose` usage:

```bash
# Build and start postgres + backend:
docker compose up --build

# Stop and remove containers (preserves DB volume):
docker compose down
```

Ports:
- Backend: `8000` -> container `8000`
- Postgres: `5432` -> container `5432`
- Ollama: `11434` -> container `11434`

---

## Endpoints (current)

- **Chat endpoint**: `POST /api/v1/chat` — conversational chat powered by LangChain + Ollama (see `backend/app/api/v1/chat_api.py`).
- **Web agent endpoint**: `POST /api/v1/web` — fetches web content and summarizes (see `backend/wingman_edge_agents/agents/web_agent.py`).

These endpoints are intentionally separated to keep agent responsibilities clear. The project includes a Telegram bot (`telegram/main.py`) that demonstrates a simple integration.

---

## Database & Vector Store (planned / upcoming)

> [!NOTE]
> **TODO: Database Integration**
> - Implement database models and interaction logic in `backend/database`.
> - Wire DB connection into the FastAPI app.
> - Add migrations using Alembic.

- The DB integration (Postgres + pgvector) is planned but not fully wired into the code yet. The `docker-compose.yml` and `database/initdb/` provided will initialize a Postgres DB with the `vector` extension. When you are ready to enable persistence, the backend will be extended to connect to the Postgres instance and store/retrieve embeddings.

---

## Technologies used

- **FastAPI**: HTTP API server
- **LangChain**: agent orchestration
- **Ollama**: local model inference
- **uv**: Dependency management and execution
- **SQLAlchemy**: planned DB ORM
- **Postgres + pgvector**: planned vector DB (docker-compose init included)
- **python-telegram-bot**: Telegram integration

---

## Development notes

- The repository is a work in progress: some modules are stubs or partial implementations (particularly DB persistence).
- To run on Raspberry Pi, ensure you use an image/build compatible with the Pi's architecture (arm64/armv7). The provided Dockerfile is a starting point — you may need to adjust base image tags for your Pi CPU.

---

## Resources

- See `backend/` for the FastAPI app.
- See `wingman_edge_agents/` for agent implementations and prompts.

If you'd like, I can:
- run a small edit to wire DB env vars into `backend/app` config,
- or create a minimal `.env.example` for docker-compose.

