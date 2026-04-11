import os
import re
from typing import Any, Dict, Literal, Union

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from backend.wingman_edge_agents.agents.prompts.wiki_pompt import (
    TOPIC_AGENT_SYS_PROMPT,
    TOPIC_PLACEMENT_STRUCTURE_PROMPT,
)
from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.tools.vault_raw_tools import (
    list_files_in_raw_topic,
    list_raw_topic_directories,
    read_head_of_raw_topic_note,
)
from backend.wingman_edge_agents.graph.data_models import QueryRouterOutput, TopicPlacementDecision
from backend.wingman_edge_agents.utils.ingest_save import slugify_kebab_segment
from backend.wingman_edge_agents.agents.prompts.wiki_pompt import QUERY_ROUTER_SYS_PROMPT
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def _format_agent_messages(messages: list[BaseMessage]) -> str:
    lines: list[str] = []
    for m in messages:
        role = m.type
        if isinstance(m, AIMessage):
            if m.tool_calls:
                lines.append(f"{role}: [tool_calls] {m.tool_calls}")
            if m.content:
                lines.append(f"{role}: {m.content}")
        elif isinstance(m, ToolMessage):
            content = str(m.content)
            if len(content) > 6000:
                content = content[:6000] + "\n... [truncated]"
            lines.append(f"{role}({m.name}): {content}")
        else:
            content = m.content
            if isinstance(content, list):
                content = " ".join(str(x) for x in content)
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


class RouterAgents:

    router_llm = os.getenv("ROUTER_LLM", 'llama3.1:8b')
    chat_router_llm = os.getenv("CHAT_ROUTER_LLM", 'llama3.1:8b')
    topic_agent_llm = os.getenv("TOPIC_AGENT_LLM", os.getenv("ROUTER_LLM", "llama3.1:8b"))


    def __init__(self, provider: Literal["ollama", "openai", "anthropic"]):
        self.llm_client = LLMClient()
        self.provider = provider
        self.language_model = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1:8b")
        self.default_model = "llama3.1:8b"
        

    # Router: ingest | query | lint (see wiki/prompt.py)
    def query_router_llm_f(self,query: str, chat_context: str|None = "")-> Union[QueryRouterOutput, Dict[str, Any]]:
        router_llm = self.llm_client.init_ollama(
                provider=self.provider,
                model=self.router_llm or self.default_model, # this the default value
                temperature=0,
                reasoning=None
                )
        
        structured_llm_router = router_llm.with_structured_output(QueryRouterOutput)

        system_prompt = QUERY_ROUTER_SYS_PROMPT

        human_message = "User query: {query} \n chat context: {chat_context}"

        router_prompt = ChatPromptTemplate.from_messages(
            [
                ('system',system_prompt),
                ('human',human_message)
            ]
        )

        question_router = router_prompt | structured_llm_router

        route = question_router.invoke(
            {"query": query, "chat_context": chat_context}
        )

        return route

    def topic_agent(self, excerpt: str, source_description: str) -> TopicPlacementDecision:
        """
        LangChain agent: inspect vault raw/ topics via tools, then structured placement.
        ``excerpt`` must already be capped (e.g. 5000 chars) for classification.
        """
        llm = self.llm_client.init_ollama(
            model=self.topic_agent_llm,
            temperature=0,
            reasoning=None,
        )
        tools = [
            list_raw_topic_directories,
            list_files_in_raw_topic,
            read_head_of_raw_topic_note,
        ]
        agent = create_agent(
            model=llm,
            system_prompt=TOPIC_AGENT_SYS_PROMPT,
            tools=tools,
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
            ],
        )
        user_block = (
            f"Source: {source_description}\n\n"
            "Document excerpt (may be truncated for classification):\n---\n"
            f"{excerpt}\n---\n"
            "Use tools to list existing raw topic directories, then decide reuse vs new topic."
        )
        result = agent.invoke({"messages": [("user", user_block)]})
        messages = result.get("messages", [])
        transcript = _format_agent_messages(messages)
        parser_llm = self.llm_client.init_ollama(
            model=self.topic_agent_llm,
            temperature=0,
            reasoning=None,
        )
        structured = parser_llm.with_structured_output(TopicPlacementDecision)
        parse_prompt = (
            TOPIC_PLACEMENT_STRUCTURE_PROMPT
            + "\n\n## Assistant transcript\n"
            + transcript
            + "\n\n## Excerpt (for published date hints)\n"
            + excerpt[:4000]
        )
        decision = structured.invoke([HumanMessage(content=parse_prompt)])
        if not isinstance(decision, TopicPlacementDecision):
            raise TypeError(f"Expected TopicPlacementDecision, got {type(decision)}")
        topic = slugify_kebab_segment(decision.topic_directory, max_len=80)
        title = decision.note_title.strip() or "Untitled"
        pub = (decision.published_date or "").strip() or None
        if pub and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", pub):
            pub = None
        return TopicPlacementDecision(
            topic_directory=topic or "misc",
            note_title=title,
            published_date=pub,
        )


def topic_agent(
    excerpt: str,
    source_description: str,
    provider: Literal["ollama", "openai", "anthropic"] = "ollama",
) -> TopicPlacementDecision:
    """Run the topic-placement LangChain agent (wrapper around :meth:`RouterAgents.topic_agent`)."""
    return RouterAgents(provider).topic_agent(excerpt, source_description)
