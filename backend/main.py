import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.app.api.v1 import inits_api, chat_api, ollama_api
from backend.app.domain.services import ensure_database_schema

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_database_schema()
    yield


app = FastAPI(
    title="Wingman Agent on the Edge",
    description="Backend for managing Ollama models and LangGraph agents on the Rasp Pi.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ollama_api.router, tags=["ollama"])
app.include_router(chat_api.router, tags=["chat"])
app.include_router(inits_api.router, tags=["init"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Wingman Agent on the Edge API"}


if __name__ == "__main__":
    print(f"Starting server on {APP_HOST}:{APP_PORT}")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
