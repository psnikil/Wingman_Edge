"""Safe read-only tools for exploring OBSIDIAN_VAULT_PATH/raw topic folders."""

import re
from pathlib import Path

from langchain.tools import tool

from backend.wingman_edge_agents.utils.root_fs import (
    format_dir_listing,
    layer_root,
    parse_relative_segments,
    read_text_limited,
    safe_resolve_under,
)

_TOPIC_SEGMENT = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_]{0,127}$")


def _raw_root() -> Path | None:
    return layer_root("raw")


@tool(parse_docstring=True)
def list_raw_topic_directories() -> str:
    """List existing topic subdirectory names under OBSIDIAN_VAULT_PATH/raw.

    Use this first to see which topic folders already exist before choosing or reusing a topic.
    """
    root = _raw_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set; cannot list topics."
    if not root.is_dir():
        return f"No raw directory yet (expected {root})."
    names = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not names:
        return "(no topic subdirectories yet)"
    return "Existing topic directories:\n" + "\n".join(names)


@tool(parse_docstring=True)
def list_files_in_raw_topic(topic_directory: str) -> str:
    """List files inside one topic folder under raw/ (non-recursive, capped).

    Args:
        topic_directory: Name of a subdirectory of raw/ (e.g. machine-learning).
    """
    if not _TOPIC_SEGMENT.match(topic_directory):
        return "Invalid topic_directory name (use letters, numbers, hyphen; no path segments)."
    root = _raw_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    target = safe_resolve_under(root, [topic_directory])
    if target is None or not target.is_dir():
        return f"No such topic directory: {topic_directory}"
    all_entries = sorted(target.iterdir(), key=lambda p: p.name)
    entries = all_entries[:40]
    lines = [p.name + ("/" if p.is_dir() else "") for p in entries]
    return format_dir_listing(lines, len(all_entries) > 40)


@tool(parse_docstring=True)
def read_head_of_raw_topic_note(topic_directory: str, file_name: str, max_chars: int = 2500) -> str:
    """Read the beginning of one markdown file under raw/<topic_directory>/.

    Args:
        topic_directory: Subdirectory name under raw/.
        file_name: File name only (e.g. note.md), no slashes or parent paths.
        max_chars: Maximum characters to return (default 2500).
    """
    if not _TOPIC_SEGMENT.match(topic_directory):
        return "Invalid topic_directory."
    if "/" in file_name or "\\" in file_name or file_name in (".", ".."):
        return "file_name must be a plain file name."
    root = _raw_root()
    if root is None:
        return "OBSIDIAN_VAULT_PATH is not set."
    path = safe_resolve_under(root, [topic_directory, file_name])
    if path is None:
        return "Path escape rejected."
    return read_text_limited(path, max_chars)


__all__ = [
    "list_raw_topic_directories",
    "list_files_in_raw_topic",
    "read_head_of_raw_topic_note",
]
