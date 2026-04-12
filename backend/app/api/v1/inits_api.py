import shutil
import time

from fastapi import APIRouter

from backend.app.domain.services import IsInitService
from backend.app.schemas.misc import IsInit
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running, start_ollama

router = APIRouter()
is_init_service = IsInitService()


@router.get("/is_init")
async def is_initiated():
    try:
        if not is_ollama_running():
            if shutil.which("ollama"):
                start_ollama()
                for _ in range(30):
                    if is_ollama_running():
                        break
                    time.sleep(0.5)
            if not is_ollama_running():
                is_init_service.update_init(False)
                return IsInit(
                    is_init=False,
                    err_message="Ollama is not reachable at OLLAMA_BASE_URL",
                )
        is_init_service.update_init(True)
        return IsInit(is_init=True)
    except Exception as e:
        print(f" Error during initialization: {e}")
        is_init_service.update_init(False)
        return IsInit(is_init=False, err_message=str(e))
