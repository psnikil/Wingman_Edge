import os
import json
from pathlib import Path
from typing import Any, Dict, Literal, Union
from datetime import date
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from backend.wingman_edge_agents.agents.prompts.wiki_pompt import (
    QUERY_ROUTER_SYS_PROMPT,
    TOPIC_AGENT_SYS_PROMPT,
    WIKI_COMPILE_AGENT_SYS_PROMPT,
    WIKI_LINT_AGENT_SYS_PROMPT,
    WIKI_QUERY_AGENT_SYS_PROMPT,
)
from backend.wingman_edge_agents.services.edge_llm_client.llm_client import LLMClient
from backend.wingman_edge_agents.tools.vault_raw_tools import (
    list_files_in_raw_topic,
    list_raw_topic_directories,
    read_head_of_raw_topic_note,
)
from backend.wingman_edge_agents.tools.vault_wiki_tools import (
    append_wiki_log_entry,
    list_wiki_articles,
    read_wiki_file,
    write_wiki_article,
    write_wiki_index,
)
from backend.wingman_edge_agents.graph.data_models import QueryRouterOutput, TopicPlacementDecision
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

_WIKI_COMPILE_BODY_MAX = int(os.getenv("WIKI_COMPILE_BODY_MAX_CHARS", "80000"))


def _parse_agent_json_final(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return json.loads(s)


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


class NodeAgent:

    def __init__(self, provider: Literal["ollama", "openai", "anthropic"] = "ollama"):
        self.provider = provider
        self.llm_client = LLMClient()
        self.topic_agent_llm = os.getenv("WIKI_INGEST_MODEL", "llama3.1:8b")
        self.wiki_agent_llm = os.getenv(
            "WIKI_WIKI_AGENT_LLM",
            os.getenv("WIKI_INGEST_MODEL", "llama3.1:8b"),
        )
        self.query_agent_llm = os.getenv(
            "WIKI_QUERY_AGENT_LLM",
            os.getenv(
                "WIKI_WIKI_AGENT_LLM",
                os.getenv("WIKI_INGEST_MODEL", "llama3.1:8b"),
            ),
        )
        self.lint_agent_llm = os.getenv(
            "WIKI_LINT_AGENT_LLM",
            os.getenv(
                "WIKI_QUERY_AGENT_LLM",
                os.getenv(
                    "WIKI_WIKI_AGENT_LLM",
                    os.getenv("WIKI_INGEST_MODEL", "llama3.1:8b"),
                ),
            ),
        )

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
            "Use tools to list existing raw topic directories, then decide reuse vs new topic, create a new short kebab-case file name for the new note."
            "Extract the published date from the excerpt if it is present."
            "Return the data in the following JSON format:"
            "{\n\t \"topic_directory\": \"string\",\n\t \"note_title\": \"string\",\n\t \"published_date\": \"string | null\"\n}"
        )
        result = agent.invoke({"messages": [("user", user_block)]})
        messages = result.get("messages", [])
        transcript = _format_agent_messages(messages)
        final_ans = messages[-1].content
        res_json = json.loads(final_ans)
        topic = res_json.get("topic_directory")
        title = res_json.get("note_title")
        pub = res_json.get("published_date")
        
        res = TopicPlacementDecision(
            topic_directory=topic or "misc",
            note_title=title or "Untitled",
            published_date=pub,
        )
        return res

    def wiki_agent(
        self,
        *,
        ingest_markdown: str,
        vault_relative_raw_md: str,
        source_description: str,
        collected: str,
        published_display: str,
        note_title: str,
    ) -> str:
        """Compile ingest into ``wiki/`` via tools; return JSON summary string."""
        raw_path = Path(vault_relative_raw_md.replace("\\", "/"))
        raw_wikilink_path = raw_path.with_suffix("").as_posix()

        body = ingest_markdown
        truncated = False
        if len(body) > _WIKI_COMPILE_BODY_MAX:
            body = body[:_WIKI_COMPILE_BODY_MAX]
            truncated = True

        llm = self.llm_client.init_ollama(
            model=self.wiki_agent_llm,
            temperature=0,
            reasoning=None,
            num_ctx=80000,
        )
        tools = [
            list_wiki_articles,
            read_wiki_file,
            write_wiki_article,
            write_wiki_index,
            append_wiki_log_entry,
        ]
        agent = create_agent(
            model=llm,
            system_prompt=WIKI_COMPILE_AGENT_SYS_PROMPT,
            tools=tools,
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
            ],
        )
        today = date.today().isoformat()
        trunc_note = (
            f"\n\n[Ingest body truncated to {_WIKI_COMPILE_BODY_MAX} characters for this step. "
            "Rely on metadata and the start of the body; Raw wikilink must still match the path below.]\n"
            if truncated
            else ""
        )
        user_block = (
            f"Today's date (for log/index): {today}\n"
            f"Note title (from ingest): {note_title}\n"
            f"Source: {source_description}\n"
            f"Collected: {collected}\n"
            f"Published (display): {published_display}\n"
            f"Vault-relative raw file (disk path): {vault_relative_raw_md}\n"
            f"Use this path for Raw wikilinks (no .md in link): [[{raw_wikilink_path}]]\n\n"
            "Full ingest markdown (saved under raw/):\n---\n"
            f"{body}\n---{trunc_note}\n"
            "Follow the system instructions: explore wiki, write/update articles with Obsidian wikilinks and YAML tags, "
            "rewrite index.md, append log.md, then reply with ONLY the final JSON object."
        )
        result = agent.invoke({"messages": [("user", user_block)]})
        messages = result.get("messages", [])
        final_ans = messages[-1].content
        if isinstance(final_ans, list):
            final_ans = " ".join(str(x) for x in final_ans)
        try:
            summary = _parse_agent_json_final(str(final_ans))
            return json.dumps(summary)
        except (json.JSONDecodeError, TypeError, ValueError):
            transcript = _format_agent_messages(messages)
            return json.dumps(
                {
                    "error": "wiki_agent_final_not_json",
                    "raw_final": str(final_ans)[:2000],
                    "transcript_tail": transcript[-8000:],
                }
            )

    def query_agent(self, user_question: str) -> str:
        """Answer from ``wiki/`` via read-only tools; return markdown for ``WikiState.generation``."""
        llm = self.llm_client.init_ollama(
            model=self.query_agent_llm,
            temperature=0,
            reasoning=None,
            num_ctx=80000,
        )
        tools = [
            list_wiki_articles,
            read_wiki_file,
        ]
        agent = create_agent(
            model=llm,
            system_prompt=WIKI_QUERY_AGENT_SYS_PROMPT,
            tools=tools,
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
            ],
        )
        user_block = (
            "Answer using only wiki files you read with tools.\n\n"
            f"User question:\n---\n{user_question}\n---"
        )
        result = agent.invoke({"messages": [("user", user_block)]})
        messages = result.get("messages", [])
        if not messages:
            return "The wiki query agent returned no messages."
        final_ans = messages[-1].content
        if isinstance(final_ans, list):
            final_ans = " ".join(str(x) for x in final_ans)
        text = str(final_ans).strip()
        return text if text else "The wiki does not contain relevant information for this question."

    def lint_agent(
        self,
        *,
        trigger: Literal["post_ingest", "standalone"],
        user_message: str,
        preflight_scan_json: str,
        post_ingest_context: str = "",
    ) -> str:
        """Lint ``wiki/`` via tools; return JSON summary string for ``WikiState.wiki_lint_generation``."""
        llm = self.llm_client.init_ollama(
            model=self.lint_agent_llm,
            temperature=0,
            reasoning=None,
            num_ctx=80000,
        )
        tools = [
            list_wiki_articles,
            read_wiki_file,
            write_wiki_article,
            write_wiki_index,
            append_wiki_log_entry,
            list_raw_topic_directories,
            list_files_in_raw_topic,
            read_head_of_raw_topic_note,
        ]
        agent = create_agent(
            model=llm,
            system_prompt=WIKI_LINT_AGENT_SYS_PROMPT,
            tools=tools,
            middleware=[
                ToolRetryMiddleware(max_retries=2, backoff_factor=1.5, initial_delay=0.5),
                ModelRetryMiddleware(max_retries=2),
            ],
        )
        today = date.today().isoformat()
        ctx = (
            f"\nPost-ingest context (raw path / title hints):\n{post_ingest_context}\n"
            if post_ingest_context.strip()
            else ""
        )
        user_block = (
            f"Today's date: {today}\n"
            f"Trigger: {trigger} (post_ingest = after an ingest compile on this run; standalone = user asked for lint only).\n"
            f"User message / focus:\n---\n{user_message}\n---\n"
            f"{ctx}"
            "Preflight scan (JSON, from disk; trust structure):\n---\n"
            f"{preflight_scan_json}\n---\n"
            "Follow the system instructions: use tools, append log.md, then reply with ONLY the final JSON object."
        )
        result = agent.invoke({"messages": [("user", user_block)]})
        messages = result.get("messages", [])
        final_ans = messages[-1].content if messages else ""
        if isinstance(final_ans, list):
            final_ans = " ".join(str(x) for x in final_ans)
        try:
            summary = _parse_agent_json_final(str(final_ans))
            return json.dumps(summary)
        except (json.JSONDecodeError, TypeError, ValueError):
            transcript = _format_agent_messages(messages)
            return json.dumps(
                {
                    "error": "lint_agent_final_not_json",
                    "raw_final": str(final_ans)[:2000],
                    "transcript_tail": transcript[-8000:],
                },
            )


def topic_agent(
    excerpt: str,
    source_description: str,
    provider: Literal["ollama", "openai", "anthropic"] = "ollama",
) -> TopicPlacementDecision:
    """Run the topic-placement LangChain agent (wrapper around :meth:`NodeAgent.topic_agent`)."""
    return NodeAgent(provider).topic_agent(excerpt, source_description)
