import os
from datetime import datetime
from typing import Annotated, List, Union,Literal,Dict,Any

from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage,AnyMessage,HumanMessage,AIMessage
from langchain.agents import create_agent

from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.agents.prompts.chat_prompt import CHAT_SYS_PROMPT,THINK_SYS_PROMPT
from backend.wingman_edge_agents.tools.think_tools import think_tool

from dotenv import load_dotenv
load_dotenv()

class ChatAgent:

    chat_llm = os.getenv("CHAT_LLM", "qwen3.5:2b")

    def __init__(self, provider: str = "ollama",**kwargs):
        self.llm_client = LLMClient()
        self.provider = provider
        self.chat_model = self.chat_llm
        super().__init__(**kwargs)

    def chat_llm_f(self, model:str, query:str, context:str|None=None)->str:

        chat_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
        )

        system_prompt = (
            CHAT_SYS_PROMPT + "\n"
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

    async def chat_agent_af(
        self, model: str, query: str, context: str | None = None
    ) -> str:
        """Async entry used by HTTP layer; wraps sync LLM call."""
        return self.chat_llm_f(model=model, query=query, context=context)

    def think_chat_llm_f(self, model:str, query:str, context:str|None=None)->str:

        think_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
        )
        tools = [think_tool]

        system_prompt = (
            THINK_SYS_PROMPT + "\n" +
            "Todays date is {date} and the time is {time}"
        )


        think_agent = create_agent(
            model=think_llm,
            tools=tools,
            system_prompt=system_prompt.format(
                date=datetime.now().strftime("%Y-%m-%d"),
                time=datetime.now().strftime("%H:%M:%S")
            ),
            # TODO: add middleware
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
        response = think_agent.invoke({"messages":messages})
        return response['messages'][-1].content


    async def think_chat_llm_af(self, model:str, query:str, context:str|None=None)->str:

        think_llm = self.llm_client.init_ollama(
            model=model,
            temperature=0,
        )
        tools = [think_tool]

        system_prompt = (
            THINK_SYS_PROMPT + "\n" +
            "Todays date is {date} and the time is {time}"
        )


        think_agent = create_agent(
            model=think_llm,
            tools=tools,
            system_prompt=system_prompt.format(
                date=datetime.now().strftime("%Y-%m-%d"),
                time=datetime.now().strftime("%H:%M:%S")
            ),
            # TODO: add middleware
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
        response = await think_agent.ainvoke({"messages":messages})
        return response['messages'][-1].content

            
        



    
