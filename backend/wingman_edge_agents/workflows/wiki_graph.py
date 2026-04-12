from langgraph.graph import END, START, StateGraph

from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.graph.wiki_nodes import (
    ingest_compile,
    ingest_fetch,
    query_node,
    wiki_lint,
)
from backend.wingman_edge_agents.graph.wiki_router import query_router


def _route_after_router(state: WikiState) -> str:
    route = (state.router_route or "").strip().lower()
    if route == "ingest":
        return "ingest"
    if route == "query":
        return "query"
    return "lint"


def build_wiki_graph():
    graph = StateGraph(WikiState)
    graph.add_node("query_router", query_router)
    graph.add_node("ingest_fetch", ingest_fetch)
    graph.add_node("ingest_compile", ingest_compile)
    graph.add_node("wiki_lint", wiki_lint)
    graph.add_node("query_node", query_node)
    graph.add_edge(START, "query_router")
    graph.add_conditional_edges(
        "query_router",
        _route_after_router,
        {
            "ingest": "ingest_fetch",
            "query": "query_node",
            "lint": "wiki_lint",
        },
    )
    graph.add_edge("query_node", "wiki_lint")
    graph.add_edge("ingest_fetch", "ingest_compile")
    graph.add_edge("ingest_compile", "wiki_lint")
    graph.add_edge("wiki_lint", END)
    return graph.compile()
