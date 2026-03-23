from fastapi import APIRouter, HTTPException,Depends
from backend.wingman_edge_agents.services.edge_llm_client.ollama_client import list_ollama_models,is_ollama_running

router = APIRouter()


@router.get("/list_ollama_models", response_model=list)
def ollama_models():
    try:
        if not is_ollama_running():
            raise 'Ollama not started'
        
        ollama_models = list_ollama_models()

        return ollama_models
    except Exception as e:
        print('there was an error getting the ollama models:',e)
        raise e
