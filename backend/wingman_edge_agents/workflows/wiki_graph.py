from langgraph.graph import END, START, StateGraph

from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.graph.wiki_nodes import ingest_fetch
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
    graph.add_edge(START, "query_router")
    graph.add_conditional_edges(
        "query_router",
        _route_after_router,
        {
            "ingest": "ingest_fetch",
            "query": END,
            "lint": END,
        },
    )
    graph.add_edge("ingest_fetch", END)
    return graph.compile()
