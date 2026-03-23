import os
from datetime import datetime
from typing import Annotated, List, Union,Literal,Dict,Any

from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage,AnyMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent
from langchain_tavily import TavilySearch

from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.agents.prompts.web_prompt import WEB_AGENT_SYS_PROMPT
from backend.wingman_edge_agents.tools.web_tools import web_search_tavily,web_search_duckduckgo


from dotenv import load_dotenv
load_dotenv()


class WebAgent:

    web_llm = os.getenv("WEB_LLM", "qwen3.5:2b")

    def __init__(self, provider: str = "ollama",**kwargs):
        self.llm_client = LLMClient(provider=provider)
        self.provider = provider
        self.web_model = web_llm
        super().__init__(**kwargs)

    async def web_llm_af(self, model:str, query:str, context:List[AnyMessage]|str|None=None)->str:

        web_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
        )
        tavily_search = TavilySearch(include_raw_content=False,max_results=5,search_depth="basic")
        tools = [tavily_search,web_search_duckduckgo]

        web_agent = create_agent(
            model=web_llm,
            tools=tools,
            system_prompt=WEB_AGENT_SYS_PROMPT,
            # TODO: add middleware
        )
        # build the context and user query into a prompt
        if context:
            for mes in context:
                if 
        response = await web_agent.ainvoke(input=query,context=context)

        return response

        

        