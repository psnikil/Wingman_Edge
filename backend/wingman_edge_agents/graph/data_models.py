from typing import Literal, Optional
from pydantic import BaseModel


class WikiState(BaseModel):
    """
    State for the wiki graph
    """

    # TODO: Need to reduce the number of fields in the state
    query: str = ""
    context: str = ""
    generation: str = ""
    data_source: str = ""
    file_path: Optional[str] = None
    router_route: str = ""
    ingest_output_path: Optional[str] = None
    wiki_generation: str = ""
    # Passed from ingest_fetch to ingest_compile (raw step metadata)
    ingest_source_description: str = ""
    ingest_collected: str = ""
    ingest_published_display: str = ""
    ingest_note_title: str = ""
    ingest_raw_topic: str = ""


class QueryRouterOutput(BaseModel):
    """
    Output for the query router
    """

    action: Literal["ingest", "query", "lint"]
    query: str


class TopicPlacementDecision(BaseModel):
    """Structured output after the topic placement agent + parser."""

    topic_directory: str
    note_title: str
    published_date: Optional[str] = None
