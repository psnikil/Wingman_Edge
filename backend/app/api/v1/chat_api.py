import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.app.infra.agents import agents_infra
from backend.app.schemas.chat import ChatRequest
from backend.wingman_edge_agents.utils.agent_limits import agent_max_seconds
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running

logger = logging.getLogger(__name__)

router = APIRouter()

agents_infra = agents_infra()


@router.post("/chat")
async def chat(request: ChatRequest):
    """Basic endpoint to handle chat requests."""
    logger.debug("the request is: ", request)
    print("the request is: ", request, flush=True)
    try:
        if not is_ollama_running():
            raise HTTPException(status_code=503, detail="Ollama is not reachable")
        logger.debug("Ollama is reachable", request.model)
        print("Ollama is reachable", request.model, flush=True)
        agent_cap = agent_max_seconds()
        chat_response = await asyncio.wait_for(
            agents_infra.think_chat_agent(
                chat_id=request.chatId, model=request.model, query=request.query
            ),
            timeout=agent_cap,
        )

        return chat_response

    except HTTPException:
        raise
    except TimeoutError:
        agent_cap = agent_max_seconds()
        raise HTTPException(
            status_code=504,
            detail=f"Agent exceeded maximum time ({int(agent_cap)}s)",
        ) from None
    except Exception as e:
        print("there was an error chatting with the ollama models:", e)
        raise HTTPException(status_code=502, detail="Chat request failed") from e


@router.post("/web_agent")
async def web_agent(request: ChatRequest):
    try:
        if not is_ollama_running():
            raise HTTPException(status_code=503, detail="Ollama is not reachable")

        agent_cap = agent_max_seconds()
        web_response = await asyncio.wait_for(
            agents_infra.web_chat_agent(
                chat_id=request.chatId, model=request.model, query=request.query
            ),
            timeout=agent_cap,
        )

        return web_response

    except HTTPException:
        raise
    except TimeoutError:
        agent_cap = agent_max_seconds()
        raise HTTPException(
            status_code=504,
            detail=f"Agent exceeded maximum time ({int(agent_cap)}s)",
        ) from None
    except Exception as e:
        print("there was an error chatting with the ollama models:", e)
        raise HTTPException(status_code=502, detail="Web agent request failed") from e
