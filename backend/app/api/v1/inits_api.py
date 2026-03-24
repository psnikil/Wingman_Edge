from fastapi import APIRouter, HTTPException
from backend.app.schemas.misc import IsInit
from backend.app.domain.services import IsInitService
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running, start_ollama, list_ollama_models

router = APIRouter()
is_init_service = IsInitService()

@router.get("/is_init")
def is_initiated():
    try:
        if not is_ollama_running():
            start_ollama()
            is_init_service.update_init(True)
        
        return IsInit(is_init=True)
    except Exception as e:
        print(f" Error during initialization: {e}")
        is_init_service.update_init(False)
        return IsInit(is_init=False, err_message=str(e))
    
