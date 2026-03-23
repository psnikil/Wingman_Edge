import os
from datetime import datetime
from typing import Annotated, List, Union,Literal,Dict,Any

from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.agents.prompts.chat_prompt import CHAT_SYSTEM_PROMPT

from dotenv import load_dotenv
load_dotenv()

class ChatAgent:

    chat_llm = os.getenv("CHAT_LLM", "qwen3.5:2b")

    def __init__(self, provider: str = "ollama",**kwargs):
        self.llm_client = LLMClient(provider=provider)
        self.provider = provider
        self.chat_model = chat_llm
        super().__init__(**kwargs)

    def chat_llm_f(self, model:str, query:str, context:str|None=None)->str:

        chat_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
        )

        system_prompt = (
            CHAT_SYSTEM_PROMPT,
            "Todays date is {date} and the time is {time}"
        )

        if context:
            user_query = (
                "The context of the chat is:\n"
                "{context}"
                "\n"
                "The user query is: {query}"
            )
        else:
            user_query = (
                "The user query is: {query}"
            )

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_query)
        ])
        
        chat_chain = (
            chat_prompt
            | chat_llm
            | StrOutputParser()
        )

        response = chat_chain.invoke({
            "context": context,
            "query": query,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S")
        })

        return response
        



    
