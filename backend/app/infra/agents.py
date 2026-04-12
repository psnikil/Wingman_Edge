import logging
import os
import uuid
from datetime import datetime
from typing import List, Union

from backend.app.domain.services import ChatService
from backend.app.schemas.chat import Message
from backend.wingman_edge_agents.agents.chat_agent import ChatAgent
from backend.wingman_edge_agents.agents.web_agent import WebAgent

logger = logging.getLogger(__name__)

_USE_LOCAL_MEMORY = os.getenv("WINGMAN_CHAT_MEMORY_ONLY", "").lower() in (
    "1",
    "true",
    "yes",
)


def _role_label(role: str) -> str:
    r = (role or "").lower()
    return "User" if r == "user" else "AI"


def _messages_to_chat_context_str(messages: List[Message]) -> str:
    return "\n".join(f"{_role_label(m.role)}: {m.content}" for m in messages)


def _messages_to_web_context_lines(messages: List[Message]) -> list[str]:
    """Format expected by ``WebAgent.web_agent_af`` (split on first ':')."""
    return [f"{_role_label(m.role)}:{m.content}" for m in messages]


def _normalize_web_context(
    context: Union[str, List[Message], list, None],
) -> Union[List[str], str, None]:
    if not context:
        return None
    if isinstance(context, list) and context and isinstance(context[0], Message):
        return _messages_to_web_context_lines(context)
    return context


class agents_infra:
    """Routes chat/web flows to DB or in-process memory based on ``WINGMAN_CHAT_MEMORY_ONLY``."""

    def __init__(self):
        self.chat_agent = ChatAgent()
        self.web_agent = WebAgent()
        self.chat_service = ChatService()
        self._use_local_memory = _USE_LOCAL_MEMORY
        self._local_messages: dict[str, list[Message]] = {}

    def _append_local(self, chat_id: str, message: Message) -> None:
        self._local_messages.setdefault(chat_id, []).append(message)

    def get_context(self, chat_id: str):
        if self._use_local_memory:
            msgs = self._local_messages.get(chat_id, [])
            logger.info("getting context for chat_id (memory): %s", chat_id)
            return msgs if msgs else ""
        logger.info("getting context for chat_id: %s", chat_id)
        chat = self.chat_service.get_chat_byID(chat_id)
        logger.info("chat: %s", chat)
        if chat:
            return self.chat_service.get_chat_history(chat_id)
        return ""

    async def chat_agent(self, chat_id: str, model: str, query: str):
        context = self.get_context(chat_id) or ""
        logger.debug("context: %s", context)
        print("context: ", context, flush=True)

        ctx_str = (
            _messages_to_chat_context_str(context)
            if isinstance(context, list)
            else (context or None)
        )

        if self._use_local_memory:
            if not context:
                agent_res = await self.chat_agent.chat_agent_af(
                    model=model, query=query
                )
                self._append_local(
                    chat_id,
                    Message(
                        messageId=str(uuid.uuid4()),
                        content=agent_res,
                        role="assistant",
                        timestamp=datetime.now(),
                    ),
                )
                return agent_res
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=query,
                    role="user",
                    timestamp=datetime.now(),
                ),
            )
            agent_res = await self.chat_agent.chat_agent_af(
                model=model, query=query, context=ctx_str
            )
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=agent_res,
                    role="assistant",
                    timestamp=datetime.now(),
                ),
            )
            return agent_res

        if not context:
            self.chat_service.create_chat(chat_id=chat_id, userPrompt=query)
            agent_res = await self.chat_agent.chat_agent_af(model=model, query=query)
            agent_message = Message(
                messageId=str(uuid.uuid4()),
                content=agent_res,
                role="assistant",
                timestamp=datetime.now(),
            )
            self.chat_service.add_chat_message(
                chat_id=chat_id, message=agent_message
            )
            return agent_res

        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=query,
                role="user",
                timestamp=datetime.now(),
            ),
        )
        agent_res = await self.chat_agent.chat_agent_af(
            model=model, query=query, context=ctx_str
        )
        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=agent_res,
                role="assistant",
                timestamp=datetime.now(),
            ),
        )
        return agent_res

    async def web_chat_agent(self, chat_id: str, model: str, query: str):
        context = self.get_context(chat_id)
        web_ctx = _normalize_web_context(context if context else None)

        if self._use_local_memory:
            if not context:
                agent_res = await self.web_agent.web_agent_af(
                    model=model, query=query
                )
                self._append_local(
                    chat_id,
                    Message(
                        messageId=str(uuid.uuid4()),
                        content=agent_res,
                        role="assistant",
                        timestamp=datetime.now(),
                    ),
                )
                return agent_res
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=query,
                    role="user",
                    timestamp=datetime.now(),
                ),
            )
            agent_res = await self.web_agent.web_agent_af(
                model=model, query=query, context=web_ctx
            )
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=agent_res,
                    role="assistant",
                    timestamp=datetime.now(),
                ),
            )
            return agent_res

        if not context:
            self.chat_service.create_chat(chat_id=chat_id, userPrompt=query)
            agent_res = await self.web_agent.web_agent_af(model=model, query=query)
            self.chat_service.add_chat_message(
                chat_id=chat_id,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    content=agent_res,
                    role="assistant",
                    timestamp=datetime.now(),
                ),
            )
            return agent_res

        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=query,
                role="user",
                timestamp=datetime.now(),
            ),
        )
        agent_res = await self.web_agent.web_agent_af(
            model=model, query=query, context=web_ctx
        )
        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=agent_res,
                role="assistant",
                timestamp=datetime.now(),
            ),
        )
        return agent_res

    async def think_chat_agent(self, chat_id: str, model: str, query: str):
        context = self.get_context(chat_id)
        web_ctx = _normalize_web_context(context if context else None)

        if self._use_local_memory:
            if not context:
                agent_res = await self.web_agent.think_web_agent_af(
                    model=model, query=query
                )
                self._append_local(
                    chat_id,
                    Message(
                        messageId=str(uuid.uuid4()),
                        content=agent_res,
                        role="assistant",
                        timestamp=datetime.now(),
                    ),
                )
                return agent_res
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=query,
                    role="user",
                    timestamp=datetime.now(),
                ),
            )
            agent_res = await self.web_agent.think_web_agent_af(
                model=model, query=query, context=web_ctx
            )
            self._append_local(
                chat_id,
                Message(
                    messageId=str(uuid.uuid4()),
                    content=agent_res,
                    role="assistant",
                    timestamp=datetime.now(),
                ),
            )
            return agent_res

        if not context:
            self.chat_service.create_chat(chat_id=chat_id, userPrompt=query)
            agent_res = await self.web_agent.think_web_agent_af(
                model=model, query=query
            )
            self.chat_service.add_chat_message(
                chat_id=chat_id,
                message=Message(
                    messageId=str(uuid.uuid4()),
                    content=agent_res,
                    role="assistant",
                    timestamp=datetime.now(),
                ),
            )
            return agent_res

        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=query,
                role="user",
                timestamp=datetime.now(),
            ),
        )
        agent_res = await self.web_agent.think_web_agent_af(
            model=model, query=query, context=web_ctx
        )
        self.chat_service.add_chat_message(
            chat_id=chat_id,
            message=Message(
                messageId=str(uuid.uuid4()),
                content=agent_res,
                role="assistant",
                timestamp=datetime.now(),
            ),
        )
        return agent_res
