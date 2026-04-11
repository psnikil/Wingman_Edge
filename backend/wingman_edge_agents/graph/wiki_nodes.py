import os

from backend.wingman_edge_agents.agents.wiki_agent import RouterAgents
from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.utils import wiki_utils
from backend.wingman_edge_agents.utils.ingest_save import (
    build_ingest_markdown,
    clean_formatting_noise,
    save_to_obsidian_raw,
    slugify_kebab_segment,
)
from datetime import date


_TOPIC_EXCERPT_MAX = 5000


def ingest_fetch(state: WikiState) -> WikiState:
    path = wiki_utils.resolve_ingest_path(state.query, state.file_path)
    if path is not None:
        extracted = wiki_utils.ingest_from_path(path)
        source_desc = f"file:{path}"
    elif wiki_utils.is_http_url(state.query):
        extracted = wiki_utils.extract_url_with_playwright(state.query.strip())
        source_desc = state.query.strip()
    else:
        extracted = state.query
        source_desc = "inline-query"

    excerpt = extracted[:_TOPIC_EXCERPT_MAX] if len(extracted) > _TOPIC_EXCERPT_MAX else extracted

    router_agents = RouterAgents(provider="ollama")
    placement = router_agents.topic_agent(excerpt, source_desc)

    collected = date.today().isoformat()
    published = placement.published_date
    published_display = published if published else "Unknown"
    body = clean_formatting_noise(extracted)
    document = build_ingest_markdown(
        placement.note_title,
        source_desc,
        collected,
        published_display,
        body,
    )

    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    saved: str | None = None
    if vault:
        file_stem = slugify_kebab_segment(placement.note_title, max_len=60)
        out_path = save_to_obsidian_raw(
            vault,
            placement.topic_directory,
            file_stem,
            bool(published),
            published,
            document,
        )
        saved = str(out_path)

    return state.model_copy(
        update={
            "data_source": document,
            "generation": saved or "OBSIDIAN_VAULT_PATH not set; note not written to disk.",
            "ingest_output_path": saved,
        }
    )
