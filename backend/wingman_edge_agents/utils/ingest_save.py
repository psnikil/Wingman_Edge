"""Save ingested markdown into OBSIDIAN_VAULT_PATH/raw/<topic>/ with slug filenames."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_SLUG_SAFE = re.compile(r"[^a-z0-9]+")


def slugify_kebab_segment(title: str, max_len: int = 60) -> str:
    s = title.strip().lower()
    s = _SLUG_SAFE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
        s = "note"
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "note"


def clean_formatting_noise(body: str) -> str:
    """Light cleanup: whitespace and excessive blank lines; do not paraphrase."""
    lines = [ln.rstrip() for ln in body.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def build_ingest_markdown(
    title: str,
    source: str,
    collected: str,
    published_display: str,
    body: str,
) -> str:
    return (
        f"# {title}\n\n"
        f"> Source: {source}\n"
        f"> Collected: {collected}\n"
        f"> Published: {published_display}\n\n"
        f"{body}"
    )


def allocate_unique_filename(directory: Path, stem: str, suffix: str = ".md") -> Path:
    """Pick ``stem.md`` or ``stem-2.md``, ``stem-3.md``, … if the file exists."""
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = directory / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def save_to_obsidian_raw(
    vault_path: str,
    topic_directory: str,
    file_stem: str,
    use_date_prefix: bool,
    date_prefix: Optional[str],
    markdown_document: str,
) -> Path:
    raw = Path(vault_path).expanduser().resolve() / "raw" / topic_directory
    raw.mkdir(parents=True, exist_ok=True)
    if use_date_prefix and date_prefix:
        stem = f"{date_prefix}-{file_stem}"
    else:
        stem = file_stem
    path = allocate_unique_filename(raw, stem, ".md")
    path.write_text(markdown_document, encoding="utf-8")
    return path
