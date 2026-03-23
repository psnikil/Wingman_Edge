from fastapi import APIRouter, HTTPException,Depends

from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.utils.ollama_client import is_ollama_running,list_ollama_models
from backend.wingman_edge_agents.agents.chat_agent import ChatAgent
from backend.wingman_edge_agents.agents.web_agent import WebAgent


router = APIRouter()


@router.post("/chat")
def chat(request:ChatRequest):
    """ Basic endpoint to handle chat requests. This will be the main endpoint for the frontend to interact with the LLM. """
    try:
        if not is_ollama_running():
            raise 'Ollama not started'
        
        chat_agent = ChatAgent()

        chat_response = chat_agent.chat_llm_f(model=request.model,query=request.query)

        return chat_response

        
    except Exception as e:
        print('there was an error chatting with the ollama models:',e)
        raise e

@router.post("/web_agent")
def web_agent(request:WebAgentRequest):
    try:
        if not is_ollama_running():
            raise 'Ollama not started'
        
        web_agent = WebAgent()

        web_response = web_agent.web_llm_af(model=request.model,query=request.query,context=request.context)

        return web_response

        
    except Exception as e:
        print('there was an error chatting with the ollama models:',e)
        raise e
