import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend.app.api.v1 import inits_api, chat_api, ollama_api
from dotenv import load_dotenv
load_dotenv()


app = FastAPI(
    title="Wingman Agent on the Edge",
    description="Backend for managing Ollama models and LangGraph agents on the Rasp Pi.",
    version="1.0.0"
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
    # Use APP_HOST/APP_PORT to avoid conflicts with system env vars like HOST
    app_host = os.getenv("APP_HOST", "0.0.0.0")
    app_port = int(os.getenv("APP_PORT", "8000"))
    
    print(f"Starting server on {app_host}:{app_port}")
    uvicorn.run(app, host=app_host, port=app_port)
