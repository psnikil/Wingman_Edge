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
from backend.wingman_edge_agents.utils.wiki_lint_scan import scan_wiki_lint
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


def query_node(state: WikiState) -> WikiState:
    """Read flat ``wiki/*.md`` via tools and synthesize an answer into ``generation``."""
    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if not vault:
        msg = "OBSIDIAN_VAULT_PATH not set; cannot query the wiki on disk."
        return state.model_copy(update={"generation": msg})

    vault_path = Path(vault).expanduser().resolve()
    try:
        ensure_wiki_scaffold(vault_path)
    except Exception as e:
        return state.model_copy(update={"generation": f"Wiki scaffold failed: {e}"})

    question = (state.query or "").strip()
    if not question:
        return state.model_copy(update={"generation": "No question text after routing; nothing to query."})

    try:
        answer = NodeAgent(provider="ollama").query_agent(question)
    except Exception as e:
        answer = f"Wiki query failed: {e}"

    return state.model_copy(update={"generation": answer})


def wiki_lint(state: WikiState) -> WikiState:
    """Run wiki hygiene after ingest compile or from router ``lint``."""
    vault = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if not vault:
        skipped = json.dumps({"skipped": True, "reason": "no_vault"})
        return state.model_copy(update={"wiki_lint_generation": skipped})

    vault_path = Path(vault).expanduser().resolve()
    try:
        ensure_wiki_scaffold(vault_path)
    except Exception as e:
        return state.model_copy(
            update={
                "wiki_lint_generation": json.dumps(
                    {"error": "wiki_lint_scaffold_failed", "detail": str(e)},
                ),
            },
        )

    scan = scan_wiki_lint(vault_path)
    route = (state.router_route or "").strip().lower()
    trigger = "post_ingest" if route == "ingest" else "standalone"
    user_message = (state.query or "").strip() or "(no user message; run full wiki lint)"
    post_ctx_parts: list[str] = []
    if state.ingest_output_path:
        post_ctx_parts.append(f"ingest_output_path: {state.ingest_output_path}")
    if state.ingest_note_title:
        post_ctx_parts.append(f"ingest_note_title: {state.ingest_note_title}")
    post_ingest_context = "\n".join(post_ctx_parts)

    scan_json = json.dumps(scan.to_dict(), indent=2)
    try:
        lint_out = NodeAgent(provider="ollama").lint_agent(
            trigger=trigger,
            user_message=user_message,
            preflight_scan_json=scan_json,
            post_ingest_context=post_ingest_context,
        )
    except Exception as e:
        lint_out = json.dumps({"error": "wiki_lint_failed", "detail": str(e)})

    prior = (state.generation or "").strip()
    lint_line = f"wiki_lint: {lint_out}"
    generation_msg = f"{prior}\n{lint_line}" if prior else lint_line

    return state.model_copy(
        update={
            "wiki_lint_generation": lint_out,
            "generation": generation_msg,
        },
    )
