import json
import os
from pathlib import Path
from typing import Any

from backend.wingman_edge_agents.agents.wiki_agent import NodeAgent
from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.tools.vault_wiki_tools import ensure_wiki_scaffold
from backend.wingman_edge_agents.utils import wiki_utils
from backend.wingman_edge_agents.utils.ingest_save import (
    build_ingest_markdown,
    clean_formatting_noise,
    save_to_obsidian_raw,
    slugify_kebab_segment,
)
from backend.wingman_edge_agents.utils.wiki_ingest_fallback import (
    ensure_index_wikilinks_for_flat_wiki,
    ensure_wiki_fallback_article,
)
from datetime import date


_TOPIC_EXCERPT_MAX = 5000


def ingest_fetch(state: WikiState) -> WikiState:
    """Extract content, place topic, build markdown, save under ``raw/`` only."""
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

    node_agents = NodeAgent(provider="ollama")
    placement = node_agents.topic_agent(excerpt, source_desc)

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
        generation_msg = saved
    else:
        generation_msg = "OBSIDIAN_VAULT_PATH not set; note not written to disk."

    return state.model_copy(
        update={
            "data_source": document,
            "generation": generation_msg,
            "ingest_output_path": saved,
            "ingest_source_description": source_desc,
            "ingest_collected": collected,
            "ingest_published_display": published_display,
            "ingest_note_title": placement.note_title,
            "ingest_raw_topic": placement.topic_directory,
            "wiki_generation": "",
        }
    )


def ingest_compile(state: WikiState) -> WikiState:
    """Populate flat ``wiki/*.md``, ``index.md``, and ``log.md`` after a successful raw save."""
    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    saved = state.ingest_output_path
    wiki_generation = ""

    if not vault or not saved:
        wiki_generation = json.dumps(
            {"skipped": True, "reason": "no_vault_or_no_raw_file_saved"},
        )
        return state.model_copy(update={"wiki_generation": wiki_generation})

    document = state.data_source or ""
    source_desc = state.ingest_source_description or "unknown-source"
    collected = state.ingest_collected or date.today().isoformat()
    published_display = state.ingest_published_display or "Unknown"
    note_title = state.ingest_note_title or "Untitled"
    raw_topic = state.ingest_raw_topic or "misc"

    vault_path = Path(vault).expanduser().resolve()
    rel_posix = ""
    try:
        ensure_wiki_scaffold(vault_path)
        rel = Path(saved).resolve().relative_to(vault_path)
        rel_posix = rel.as_posix()
        if not rel_posix.startswith("raw/"):
            wiki_generation = json.dumps(
                {"error": "ingest_path_not_under_raw", "path": rel_posix},
            )
        else:
            wiki_generation = NodeAgent(provider="ollama").wiki_agent(
                ingest_markdown=document,
                vault_relative_raw_md=rel_posix,
                source_description=source_desc,
                collected=collected,
                published_display=published_display,
                note_title=note_title,
            )
    except Exception as e:
        wiki_generation = json.dumps({"error": "wiki_compile_failed", "detail": str(e)})

    if rel_posix.startswith("raw/"):
        fb = ensure_wiki_fallback_article(
            vault_path,
            rel_posix,
            raw_topic,
            note_title,
            source_desc,
            document,
        )
        if fb:
            inner: Any
            try:
                inner = json.loads(wiki_generation) if wiki_generation.strip() else {}
            except json.JSONDecodeError:
                inner = wiki_generation
            wiki_generation = json.dumps(
                {"fallback_stub": fb, "wiki_agent_output": inner},
            )

    if vault and saved:
        ensure_index_wikilinks_for_flat_wiki(vault_path)

    prior = (state.generation or "").strip()
    compile_line = f"wiki_compile: {wiki_generation}"
    generation_msg = f"{prior}\n{compile_line}" if prior else compile_line

    return state.model_copy(
        update={
            "generation": generation_msg,
            "wiki_generation": wiki_generation,
        },
    )
