from fastapi import APIRouter, HTTPException,Depends


from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running,list_ollama_models
from backend.app.infra.agents import agents_infra

from backend.app.schemas.chat import ChatRequest


router = APIRouter()
# TODO: maybe init the llm here and pass it through the agent object

agents_infra = agents_infra()

@router.post("/chat")
async def chat(request:ChatRequest):
    """ Basic endpoint to handle chat requests. This will be the main endpoint for the frontend to interact with the LLM. """
    print('the request is: ', request)
    try:
        if not is_ollama_running():
            raise 'Ollama not started'
        
        chat_response = agents_infra.think_chat_agent(chat_id=request.chatId,model=request.model,query=request.query)

        return chat_response

        
    except Exception as e:
        print('there was an error chatting with the ollama models:',e)
        raise e

@router.post("/web_agent")
async def web_agent(request:ChatRequest):
    try:
        if not is_ollama_running():
            raise 'Ollama not started'
        
        web_response = agents_infra.web_agent(chat_id=request.chatId,model=request.model,query=request.query)

        return web_response

        
    except Exception as e:
        print('there was an error chatting with the ollama models:',e)
        raise e
