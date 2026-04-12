from fastapi import APIRouter, HTTPException

from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running, list_ollama_models

router = APIRouter()


@router.get("/list_ollama_models", response_model=list)
def ollama_models():
    if not is_ollama_running():
        raise HTTPException(status_code=503, detail="Ollama is not reachable")
    try:
        return list_ollama_models()
    except Exception as e:
        print("there was an error getting the ollama models:", e)
        raise HTTPException(status_code=502, detail="Failed to list Ollama models") from e
