"""Safe read/write tools for OBSIDIAN_VAULT_PATH/wiki (flat compiled layer: only ``wiki/*.md`` files)."""

from __future__ import annotations

import re
from pathlib import Path

from langchain.tools import tool

from backend.wingman_edge_agents.utils.root_fs import (
    format_dir_listing,
    layer_root,
    read_text_limited,
    safe_resolve_under,
    write_text_to_path,
)

_FILE_SEGMENT = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_]{0,127}$")
_ROOT_FILES = frozenset({"index.md", "log.md"})


def _wiki_root() -> Path | None:
    return layer_root("wiki")


def _is_reserved_article_name(name: str) -> bool:
    n = name.lower()
    return n in _ROOT_FILES or n == ".gitkeep"


def ensure_wiki_scaffold(vault_path: str | Path) -> Path:
    """Create ``wiki/``, ``index.md``, and ``log.md`` if missing (idempotent).

    Does not overwrite existing files. Returns resolved ``wiki/`` directory.
    """
    vault = Path(vault_path).expanduser().resolve()
    wiki = vault / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    index = wiki / "index.md"
    if not index.is_file():
        index.write_text(
            "# Knowledge Base Index\n\n",
            encoding="utf-8",
        )
    log = wiki / "log.md"
    if not log.is_file():
        log.write_text(
            "# Wiki Log\n\n",
            encoding="utf-8",
        )
    return wiki


@tool(parse_docstring=False)
def list_wiki_articles(max_files: int = 40) -> str:
    """List markdown article file names directly under wiki/ (excludes index.md and log.md).

    There are no subfolders under wiki/: every article is ``wiki/<name>.md``.
    """
    root = _wiki_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set; cannot list wiki articles."
    if not root.is_dir():
        return f"No wiki directory yet (expected {root})."
    names = sorted(
        p.name
        for p in root.iterdir()
        if p.is_file() and p.suffix.lower() == ".md" and not _is_reserved_article_name(p.name)
    )[: max(1, min(max_files, 200))]
    if not names:
        return "Wiki article files (flat):\n(no wiki article .md files yet at wiki root)"
    total = sum(
        1
        for p in root.iterdir()
        if p.is_file() and p.suffix.lower() == ".md" and not _is_reserved_article_name(p.name)
    )
    body = format_dir_listing(names, total > len(names))
    return "Wiki article files (flat):\n" + body


@tool(parse_docstring=False)
def read_wiki_file(file_name: str, max_chars: int = 32000) -> str:
    """Read one file under wiki/: ``index.md``, ``log.md``, or a flat article ``*.md``.

    Args:
        file_name: Plain file name only (e.g. ``index.md``, ``my-note.md``).
        max_chars: Maximum characters to return.
    """
    if "/" in file_name or "\\" in file_name or file_name in (".", ".."):
        return "file_name must be a plain file name (no path segments)."
    if not file_name.lower().endswith(".md"):
        return "file_name must end with .md"
    if file_name.lower() not in _ROOT_FILES:
        if _is_reserved_article_name(file_name):
            return "Invalid file_name."
        if not _FILE_SEGMENT.match(file_name.removesuffix(".md")):
            return "Invalid file_name."
    root = _wiki_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    path = safe_resolve_under(root, [file_name])
    if path is None:
        return "Path escape rejected."
    if file_name.lower() in _ROOT_FILES and not path.is_file():
        return f"Missing {file_name}; run scaffold or create it first."
    return read_text_limited(path, max_chars)


@tool(parse_docstring=False)
def write_wiki_article(file_name: str, content: str) -> str:
    """Write or overwrite a markdown article at wiki/<file_name> (flat; no subfolders).

    Args:
        file_name: Kebab-style name ending in .md (e.g. ``transformers-overview.md``).
        content: Full markdown body to write.
    """
    if "/" in file_name or "\\" in file_name or file_name in (".", ".."):
        return "file_name must be a plain file name (no path segments)."
    if not file_name.lower().endswith(".md"):
        return "file_name must end with .md"
    if _is_reserved_article_name(file_name):
        return "Cannot write index.md or log.md with this tool; use write_wiki_index or append_wiki_log_entry."
    stem = file_name.removesuffix(".md")
    if not _FILE_SEGMENT.match(stem):
        return "Invalid file_name (use letters, numbers, hyphen; single segment only)."
    root = _wiki_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    root.mkdir(parents=True, exist_ok=True)
    path = safe_resolve_under(root, [file_name])
    if path is None:
        return "Path escape rejected."
    err = write_text_to_path(path, content, append=False)
    if err.startswith("Write error"):
        return err
    return f"Wrote {path.relative_to(root.parent)}"


@tool(parse_docstring=False)
def write_wiki_index(content: str) -> str:
    """Overwrite wiki/index.md with the given markdown content."""
    root = _wiki_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    path = safe_resolve_under(root, ["index.md"])
    if path is None:
        return "Invalid path."
    err = write_text_to_path(path, content, append=False)
    if err.startswith("Write error"):
        return err
    return f"Wrote {path.relative_to(root.parent)}"


@tool(parse_docstring=False)
def append_wiki_log_entry(markdown_block: str) -> str:
    """Append a markdown block to wiki/log.md (creates file if missing).

    Args:
        markdown_block: Text to append; should include leading newlines or headings as needed.
    """
    root = _wiki_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    path = safe_resolve_under(root, ["log.md"])
    if path is None:
        return "Invalid path."
    root.mkdir(parents=True, exist_ok=True)
    err = write_text_to_path(path, markdown_block, append=True)
    if err.startswith("Write error"):
        return err
    return "Appended to wiki/log.md"


__all__ = [
    "append_wiki_log_entry",
    "ensure_wiki_scaffold",
    "list_wiki_articles",
    "read_wiki_file",
    "write_wiki_article",
    "write_wiki_index",
]
