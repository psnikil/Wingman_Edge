"""Path-safe vault and workspace file primitives (shared by vault_* and file_tools)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Sequence

VaultLayer = Literal["raw", "wiki"]


def vault_root() -> Path | None:
    v = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if not v:
        return None
    return Path(v).expanduser().resolve()


def layer_root(layer: VaultLayer) -> Path | None:
    base = vault_root()
    if base is None:
        return None
    return (base / layer).resolve()


def parse_relative_segments(relative: str) -> list[str] | None:
    parts = [p for p in relative.replace("\\", "/").split("/") if p and p != "."]
    if not parts:
        return None
    if any(p == ".." for p in parts):
        return None
    return parts


def safe_resolve_under(base: Path, parts: Sequence[str]) -> Path | None:
    """Resolve ``base / parts`` and require result stays under ``base``."""
    try:
        target = base.joinpath(*parts).resolve()
        target.relative_to(base.resolve())
    except (OSError, ValueError):
        return None
    return target


def read_text_limited(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return f"Not a file: {path.name}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"Read error: {e}"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def write_text_to_path(path: Path, content: str, *, append: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if append and path.is_file():
            existing = path.read_text(encoding="utf-8", errors="replace")
            if existing and not existing.endswith("\n"):
                existing += "\n"
            path.write_text(existing + content, encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
    except OSError as e:
        return f"Write error: {e}"
    return f"Wrote {path}"


def format_dir_listing(entries: list[str], truncated: bool) -> str:
    out = "\n".join(entries) if entries else "(empty)"
    if truncated:
        out += "\n... (truncated)"
    return out
