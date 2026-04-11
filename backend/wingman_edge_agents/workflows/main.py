import json
import os
from pathlib import Path

from dotenv import load_dotenv

from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.workflows.wiki_graph import build_wiki_graph

load_dotenv()

VAULT = os.getenv("OBSIDIAN_VAULT_PATH", "/home/nikil/Documents/LLM_wiki")
RAW_ROOT = Path(VAULT) / "raw"
WIKI_ROOT = Path(VAULT) / "wiki"
TEST_FILE = "/home/nikil/Documents/Projects/Agent_Orchestrator/data/session_2e62c042.md"
TEST_URL = "/home/nikil/Documents/Projects/Wingman_Edge/docs/LLM_WIKI_IMPLEMENTATION.md"


def _collect_md_under_raw() -> list[Path]:
    if not RAW_ROOT.is_dir():
        return []
    return sorted(RAW_ROOT.rglob("*.md"))


def _wiki_subdirs() -> list[Path]:
    if not WIKI_ROOT.is_dir():
        return []
    return sorted(p for p in WIKI_ROOT.iterdir() if p.is_dir())


def _wiki_flat_article_paths() -> list[Path]:
    """Article markdown files directly under ``wiki/`` (not ``index.md`` / ``log.md``)."""
    if not WIKI_ROOT.is_dir():
        return []
    root = WIKI_ROOT.resolve()
    return sorted(
        p
        for p in WIKI_ROOT.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".md"
        and p.name.lower() not in ("index.md", "log.md")
    )


def main() -> None:
    load_dotenv()
    os.environ["OBSIDIAN_VAULT_PATH"] = VAULT
    os.environ["WIKI_VERIFY_INGEST"] = "1"
    RAW_ROOT.mkdir(parents=True, exist_ok=True)

    before = set(_collect_md_under_raw())
    graph = build_wiki_graph()
    last_final: dict | None = None

    cases: list[tuple[str, WikiState]] = [
        (
            "file ingest",
            WikiState(
                query="Ingest this markdown file into the vault raw tree.",
                file_path=TEST_FILE,
            ),
        ),
        (
            "url ingest",
            WikiState(
                query=TEST_URL,
                file_path=None,
            ),
        ),
    ]

    try:
        for label, initial in cases:
            print(f"\n========== CASE: {label} ==========")
            final = graph.invoke(initial)
            last_final = final
            route = final.get("router_route", "")
            path = final.get("ingest_output_path")
            print("router_route:", route)
            print("ingest_output_path:", path)
            print("generation:", final.get("generation"))
            print("wiki_generation:", final.get("wiki_generation"))
            if path:
                p = Path(path)
                assert p.suffix == ".md", f"Expected .md, got {p}"
                assert p.resolve().is_relative_to(RAW_ROOT.resolve()), (
                    f"Expected under {RAW_ROOT}, got {p}"
                )
            ds = final.get("data_source") or ""
            print("data_source length:", len(ds))
            print("data_source head:", ds[:400].replace("\n", "\\n"))

        after = set(_collect_md_under_raw())
        new_files = sorted(after - before)
        print("\n========== NEW .md FILES UNDER raw/ ==========")
        for f in new_files:
            print(f.resolve())
        if len(new_files) < 2:
            raise SystemExit(
                f"Expected at least 2 new markdown files under {RAW_ROOT}, found {len(new_files)}: {new_files}"
            )
        print("\nOK: both runs produced new .md files under", RAW_ROOT)

        if not (WIKI_ROOT / "index.md").is_file() or not (WIKI_ROOT / "log.md").is_file():
            raise SystemExit(
                f"Expected wiki/index.md and wiki/log.md under {WIKI_ROOT}; "
                f"index exists={(WIKI_ROOT / 'index.md').is_file()} log exists={(WIKI_ROOT / 'log.md').is_file()}"
            )

        subdirs = _wiki_subdirs()
        if subdirs:
            raise SystemExit(
                f"wiki/ must not contain subfolders (flat layout only); found: {[str(p) for p in subdirs]}"
            )

        articles = _wiki_flat_article_paths()
        if not articles:
            wg = (last_final or {}).get("wiki_generation") or ""
            raise SystemExit(
                f"Expected at least one flat wiki article .md under {WIKI_ROOT}/. wiki_generation={wg!r}"
            )
        sample = articles[-1].read_text(encoding="utf-8", errors="replace")
        if "[[" not in sample or "]]" not in sample:
            raise SystemExit(
                f"Expected Obsidian wikilinks in wiki article {articles[-1]}; head={sample[:500]!r}"
            )
        if "#wiki" not in sample:
            raise SystemExit(
                f"Expected #wiki tag in wiki article {articles[-1]}; head={sample[:500]!r}"
            )

        index_text = (WIKI_ROOT / "index.md").read_text(encoding="utf-8", errors="replace")
        if "[[" not in index_text or "]]" not in index_text:
            raise SystemExit(
                f"Expected wiki/index.md to contain wikilink tables or links; head={index_text[:800]!r}"
            )
        stems = {p.stem for p in articles}
        if not any(f"[[wiki/{stem}" in index_text for stem in stems):
            raise SystemExit(
                f"index.md should include a wikilink like [[wiki/<stem>]] for at least one article in {stems!r}; "
                f"head={index_text[:1200]!r}"
            )

        wg = (last_final or {}).get("wiki_generation") or ""
        try:
            parsed = json.loads(wg) if isinstance(wg, str) and wg.strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict) and parsed.get("error") and not parsed.get(
            "fallback_stub"
        ):
            raise SystemExit(f"wiki_compile reported error: {parsed!r}")
        print("\nOK: flat wiki/, index.md wikilinks, articles with wikilinks and #wiki")
    finally:
        os.environ.pop("WIKI_VERIFY_INGEST", None)


if __name__ == "__main__":
    main()
