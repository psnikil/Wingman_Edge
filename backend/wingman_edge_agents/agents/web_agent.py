import os
from datetime import datetime
from typing import Annotated, List, Union,Literal,Dict,Any

import httpx
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage,AnyMessage,HumanMessage,AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware,ModelRetryMiddleware,ToolCallLimitMiddleware
from langchain_tavily import TavilySearch

from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.agents.prompts.web_prompt import WEB_AGENT_SYS_PROMPT
from backend.wingman_edge_agents.tools.web_tools import web_search_tavily,web_search_duckduckgo
from backend.wingman_edge_agents.utils.agent_limits import agent_max_seconds


from dotenv import load_dotenv
load_dotenv()


class WebAgent:

    web_llm = os.getenv("WEB_LLM", "qwen3.5:2b")

    def __init__(self, provider: str = "ollama",**kwargs):
        self.llm_client = LLMClient()
        self.provider = provider
        self.web_model = self.web_llm
        super().__init__(**kwargs)

    def _ollama_http_timeout_kwargs(self) -> dict:
        max_sec = agent_max_seconds()
        connect = min(30.0, max_sec)
        timeout = httpx.Timeout(max_sec, connect=connect)
        return {
            "async_client_kwargs": {"timeout": timeout},
            "sync_client_kwargs": {"timeout": timeout},
        }

    async def web_agent_af(self, model:str, query:str, context:List[AnyMessage]|str|None=None)->str:

        web_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
            **self._ollama_http_timeout_kwargs(),
        )
        tavily_search = TavilySearch(include_raw_content=False,max_results=5,search_depth="basic")
        tools = [tavily_search]
        current_date = datetime.now().strftime("%Y-%m-%d")
        web_agent = create_agent(
            model=web_llm,
            tools=tools,
            system_prompt=WEB_AGENT_SYS_PROMPT.format(current_date=current_date),
            # TODO: add middleware
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
                ToolCallLimitMiddleware(thread_limit=5,run_limit=3),

            ],  
        )
        # build the context and user query into a prompt
        messages = []
        if context:
            for msg in context:
                if msg.split(":")[0] == "User":
                    messages.append(HumanMessage(content=msg.split(":")[1]))
                elif msg.split(":")[0] == "AI":
                    messages.append(AIMessage(content=msg.split(":")[1])) 
        
        user_query = """
        The user query is: {query}
        """
        messages.append(HumanMessage(content=user_query.format(query=query)))    
        response = await web_agent.ainvoke({"messages":messages})
        return response['messages'][-1].content

    async def think_web_agent_af(
        self,
        model: str,
        query: str,
        context: List[AnyMessage] | str | list[str] | None = None,
    ) -> str:
        """Alias for web agent path used by ``think_chat_agent`` infra."""
        return await self.web_agent_af(model=model, query=query, context=context)

    def web_agent_f(self, model:str, query:str, context:List[AnyMessage]=[])->str:
        web_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
            **self._ollama_http_timeout_kwargs(),
        )
        tavily_search = TavilySearch(include_raw_content=False,max_results=5,search_depth="basic")
        tools = [tavily_search]
        current_date = datetime.now().strftime("%Y-%m-%d")
        web_agent = create_agent(
            model=web_llm,
            tools=tools,
            system_prompt=WEB_AGENT_SYS_PROMPT.format(current_date=current_date),
            # TODO: add middleware
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
                ToolCallLimitMiddleware(thread_limit=5,run_limit=3),
            ],
        )
        # build the context and user query into a prompt
        messages = []
        if context:
            for msg in context:
                if msg.split(":")[0] == "User":
                    messages.append(HumanMessage(content=msg.split(":")[1]))
                elif msg.split(":")[0] == "AI":
                    messages.append(AIMessage(content=msg.split(":")[1])) 
        
        user_query = """
        The user query is: {query}
        """
        messages.append(HumanMessage(content=user_query.format(query=query)))    
        response = web_agent.invoke({"messages":messages})
        return response['messages'][-1].content

        

        

        