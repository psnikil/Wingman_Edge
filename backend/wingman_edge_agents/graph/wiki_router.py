import os

from backend.wingman_edge_agents.agents.wiki_agent import RouterAgents
from backend.wingman_edge_agents.graph.data_models import QueryRouterOutput, WikiState

router_agents = RouterAgents(provider="ollama")


def query_router(state: WikiState) -> WikiState:
    """
    LLM router: sets router_route to ingest | query | lint.
    """
    print("_____________in query router_____________")

    if os.getenv("WIKI_VERIFY_INGEST", "").lower() in ("1", "true", "yes"):
        return state.model_copy(update={"router_route": "ingest", "context": "verify: forced ingest"})

    chat_context = state.context or ""
    if state.file_path:
        chat_context = (
            f"{chat_context}\n[Attachment: file path is `{state.file_path}`]\n".strip()
        )

    router_result = router_agents.query_router_llm_f(state.query, chat_context=chat_context)
    if not isinstance(router_result, QueryRouterOutput):
        raise TypeError(f"Expected QueryRouterOutput, got {type(router_result)}")

    return state.model_copy(
        update={
            "router_route": router_result.action,
            "query": router_result.query,
        }
    )
