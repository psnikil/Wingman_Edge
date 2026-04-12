"""Read-only scan of flat wiki/ for lint preflight (wikilinks, index vs disk)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from backend.wingman_edge_agents.utils.root_fs import safe_resolve_under

_TOPIC_SEGMENT = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_]{0,127}$")
_FILE_STEM = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_]{0,127}$")
_WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
_INDEX_WIKI = re.compile(r"\[\[wiki/([^\]|\s#]+)", re.IGNORECASE)

_RESERVED = frozenset({"index.md", "log.md"})


def _parse_wikilink_inner(inner: str) -> str:
    inner = inner.strip()
    if "|" in inner:
        inner = inner.split("|", 1)[0].strip()
    return inner


def _article_stems_on_disk(wiki_root: Path) -> set[str]:
    if not wiki_root.is_dir():
        return set()
    out: set[str] = set()
    for p in wiki_root.iterdir():
        if (
            p.is_file()
            and p.suffix.lower() == ".md"
            and p.name.lower() not in _RESERVED
        ):
            stem = p.stem
            if _FILE_STEM.match(stem):
                out.add(stem)
    return out


def _resolve_raw_target(vault: Path, target: str) -> tuple[bool, str]:
    """Return (exists_ok, detail). Target is like raw/topic/stem (no .md)."""
    parts = [x for x in target.split("/") if x]
    if len(parts) < 3 or parts[0].lower() != "raw":
        return False, "not_a_raw_path"
    topic = parts[1]
    if not _TOPIC_SEGMENT.match(topic):
        return False, "invalid_topic"
    stem = "/".join(parts[2:])  # allow only one more segment for file stem
    if "/" in stem:
        return False, "too_many_segments"
    if not _FILE_STEM.match(stem):
        return False, "invalid_stem"
    raw_root = (vault / "raw").resolve()
    path = safe_resolve_under(raw_root, [topic, f"{stem}.md"])
    if path is None:
        return False, "path_escape"
    return path.is_file(), str(path.relative_to(vault)) if path.is_file() else "missing"


def _resolve_wiki_target(wiki_root: Path, target: str) -> tuple[bool, str]:
    """Target like wiki/slug (no .md)."""
    parts = [x for x in target.split("/") if x]
    if len(parts) != 2 or parts[0].lower() != "wiki":
        return False, "not_wiki_slash_form"
    stem = parts[1]
    if not _FILE_STEM.match(stem):
        return False, "invalid_stem"
    path = wiki_root / f"{stem}.md"
    return path.is_file(), stem if path.is_file() else "missing"


@dataclass
class WikiLintScanResult:
    """JSON-serializable summary for the lint agent."""

    broken_wikilinks: list[dict[str, str]] = field(default_factory=list)
    index_wiki_targets: list[str] = field(default_factory=list)
    articles_on_disk: list[str] = field(default_factory=list)
    articles_missing_from_index: list[str] = field(default_factory=list)
    index_points_to_missing_article: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "broken_wikilinks": self.broken_wikilinks,
            "index_wiki_targets": self.index_wiki_targets,
            "articles_on_disk": self.articles_on_disk,
            "articles_missing_from_index": self.articles_missing_from_index,
            "index_points_to_missing_article": self.index_points_to_missing_article,
        }


def scan_wiki_lint(vault_path: str | Path) -> WikiLintScanResult:
    """Scan ``vault_path`` wiki layer; no env reads (tests pass a temp dir)."""
    vault = Path(vault_path).expanduser().resolve()
    wiki_root = vault / "wiki"
    result = WikiLintScanResult()

    if not wiki_root.is_dir():
        return result

    on_disk = _article_stems_on_disk(wiki_root)
    result.articles_on_disk = sorted(on_disk)

    index_path = wiki_root / "index.md"
    indexed_stems: set[str] = set()
    if index_path.is_file():
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        for m in _INDEX_WIKI.finditer(index_text):
            stem = m.group(1).strip().removesuffix(".md")
            if _FILE_STEM.match(stem):
                indexed_stems.add(stem)
        result.index_wiki_targets = sorted(indexed_stems)
        for stem in sorted(indexed_stems):
            if stem not in on_disk:
                result.index_points_to_missing_article.append(stem)

    for stem in sorted(on_disk - indexed_stems):
        result.articles_missing_from_index.append(stem)

    for md_path in sorted(wiki_root.iterdir()):
        if not md_path.is_file() or md_path.suffix.lower() != ".md":
            continue
        if md_path.name.lower() in _RESERVED:
            continue
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for m in _WIKILINK.finditer(text):
            target = _parse_wikilink_inner(m.group(1))
            if not target or target.startswith("#"):
                continue
            rel_file = md_path.relative_to(wiki_root).as_posix()
            if target.lower().startswith("raw/"):
                ok, detail = _resolve_raw_target(vault, target)
                if not ok:
                    result.broken_wikilinks.append(
                        {
                            "file": rel_file,
                            "target": target,
                            "reason": f"raw:{detail}",
                        },
                    )
            elif target.lower().startswith("wiki/"):
                ok, detail = _resolve_wiki_target(wiki_root, target)
                if not ok:
                    result.broken_wikilinks.append(
                        {
                            "file": rel_file,
                            "target": target,
                            "reason": f"wiki:{detail}",
                        },
                    )

    return result


__all__ = ["WikiLintScanResult", "scan_wiki_lint"]
