import os
from pathlib import Path

from dotenv import load_dotenv

from backend.wingman_edge_agents.graph.data_models import WikiState
from backend.wingman_edge_agents.workflows.wiki_graph import build_wiki_graph

load_dotenv()

VAULT = os.getenv("OBSIDIAN_VAULT_PATH", "/home/nikil/Documents/LLM_wiki")
RAW_ROOT = Path(VAULT) / "raw"
TEST_FILE = "/home/nikil/Documents/Projects/Agent_Orchestrator/data/session_2e62c042.md"
TEST_URL = "https://github.com/"


def _collect_md_under_raw() -> list[Path]:
    if not RAW_ROOT.is_dir():
        return []
    return sorted(RAW_ROOT.rglob("*.md"))


def main() -> None:
    load_dotenv()
    os.environ["OBSIDIAN_VAULT_PATH"] = VAULT
    os.environ["WIKI_VERIFY_INGEST"] = "1"
    RAW_ROOT.mkdir(parents=True, exist_ok=True)

    before = set(_collect_md_under_raw())
    graph = build_wiki_graph()

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
            route = final.get("router_route", "")
            path = final.get("ingest_output_path")
            print("router_route:", route)
            print("ingest_output_path:", path)
            print("generation:", final.get("generation"))
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
    finally:
        os.environ.pop("WIKI_VERIFY_INGEST", None)


if __name__ == "__main__":
    main()
