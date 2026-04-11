"""If the wiki compile agent skips filesystem writes, add a minimal valid flat wiki article."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from backend.wingman_edge_agents.utils.ingest_save import slugify_kebab_segment

_TOPIC_SEGMENT = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_]{0,127}$")
_RESERVED = frozenset({"index.md", "log.md"})


def _any_flat_wiki_article(wiki_root: Path) -> bool:
    root = wiki_root.resolve()
    if not root.is_dir():
        return False
    for p in root.iterdir():
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        if p.name.lower() in _RESERVED:
            continue
        return True
    return False


def ensure_wiki_fallback_article(
    vault_path: str | Path,
    vault_relative_raw_md: str,
    raw_topic_directory: str,
    note_title: str,
    source_description: str,
    overview_excerpt: str,
) -> str | None:
    """Write a minimal wiki article at ``wiki/<slug>-ingest-wiki.md`` if no articles exist yet.

    The wiki tree is **flat** (no subfolders under ``wiki/``). Returns vault-relative path or None.
    """
    topic_tag = raw_topic_directory if _TOPIC_SEGMENT.match(raw_topic_directory) else "misc"
    vault = Path(vault_path).expanduser().resolve()
    wiki_root = vault / "wiki"
    if not wiki_root.is_dir():
        return None
    if _any_flat_wiki_article(wiki_root):
        return None

    raw_path = Path(vault_relative_raw_md.replace("\\", "/"))
    raw_wikilink = raw_path.with_suffix("").as_posix()
    slug = slugify_kebab_segment(note_title, max_len=50)
    file_name = f"{slug}-ingest-wiki.md"
    article = (wiki_root / file_name).resolve()
    if article.parent != wiki_root.resolve():
        return None
    today = date.today().isoformat()
    excerpt = (overview_excerpt or "").strip()
    if len(excerpt) > 800:
        excerpt = excerpt[:800].rstrip() + "…"
    if not excerpt:
        excerpt = "Summary pending; see raw capture for full text."

    stem = file_name.removesuffix(".md")
    tags_yaml = f"""---
tags:
  - wiki
  - wiki/ingest
  - wiki/raw-topic/{topic_tag}
updated: {today}
---

#wiki #wiki/ingest

# {note_title}

> Sources: {source_description}
> Raw: [[{raw_wikilink}]]

## Overview

{excerpt}
"""
    article.write_text(tags_yaml, encoding="utf-8")
    log_path = wiki_root / "log.md"
    block = (
        f"\n## [{today}] ingest | {note_title} (fallback stub)\n"
        f"- Raw: [[{raw_wikilink}]]\n"
        f"- Article: [[wiki/{stem}|{note_title}]]\n"
    )
    existing = ""
    if log_path.is_file():
        existing = log_path.read_text(encoding="utf-8", errors="replace")
    if existing and not existing.endswith("\n"):
        existing += "\n"
    log_path.write_text(existing + block, encoding="utf-8")
    return f"wiki/{file_name}"


def ensure_index_wikilinks_for_flat_wiki(vault_path: str | Path) -> None:
    """Append index.md rows so every flat ``wiki/*.md`` article has a ``[[wiki/<stem>|…]]`` entry."""
    vault = Path(vault_path).expanduser().resolve()
    wiki_root = vault / "wiki"
    if not wiki_root.is_dir():
        return
    stems: list[str] = []
    for p in wiki_root.iterdir():
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        if p.name.lower() in _RESERVED:
            continue
        stems.append(p.stem)
    if not stems:
        return
    idx = wiki_root / "index.md"
    text = idx.read_text(encoding="utf-8", errors="replace") if idx.is_file() else ""
    today = date.today().isoformat()
    missing = [s for s in stems if f"[[wiki/{s}" not in text]
    if not missing:
        return
    block = (
        "\n## Articles\n\n"
        "| Article | Summary | Updated |\n"
        "| --- | --- | --- |\n"
        + "\n".join(
            f"| [[wiki/{s}|{s.replace('-', ' ')[:72]}]] | — | {today} |" for s in missing
        )
        + "\n"
    )
    if not text.strip():
        text = "# Knowledge Base Index\n"
    idx.write_text(text.rstrip() + block, encoding="utf-8")
