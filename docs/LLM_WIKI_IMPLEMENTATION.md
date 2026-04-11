# LLM Wiki (Karpathy pattern) — product spec for Wingman Edge

**Status:** living design doc. Treat this file as the **source of truth** for what the LLM Wiki feature is, why it exists, and how to implement the remaining pieces in this repository.

**Primary reference:** [Andrej Karpathy — *LLM Wiki* (gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

When an agent or human is implementing wiki-related behavior, they should read this document first, then the code paths listed under [Current implementation](#current-implementation).

---

## 1. The idea (from the gist)

### Problem with plain RAG

Typical “upload documents → retrieve chunks → answer” flows **re-derive** context on every question. There is little **accumulation**: cross-links, contradictions, and synthesis are not persisted as a first-class artifact.

### The LLM Wiki pattern

Instead of only indexing raw sources for retrieval, the LLM **incrementally builds and maintains a persistent wiki**: markdown pages that are structured, interlinked, and updated as new sources arrive. The wiki is a **compounding artifact**—cross-references, flagged tensions with older claims, and topical synthesis can live *between* the user and the raw sources.

### Three layers (architecture)

| Layer | Role | Mutability |
|--------|------|------------|
| **Raw sources** | Curated inputs (articles, papers, clips, files). | **Immutable** from the LLM’s perspective—the LLM reads but does not rewrite “truth” here. |
| **The wiki** | LLM-owned markdown: entities, concepts, summaries, overview, synthesis. | **LLM-maintained**; user reads; agent writes/updates. |
| **The schema** | Instructions for structure, conventions, ingest/query/lint workflows (e.g. a vault `WIKI.md`, `AGENTS.md`, or repo doc). | **Co-evolved** with the user as conventions stabilize. |

### Three operations (from the gist)

1. **Ingest** — New source arrives → agent reads it → (optionally) discusses takeaways → writes/updates wiki pages, index, entity/concept pages, and appends a **log** entry. One source may touch many pages.
2. **Query** — User asks questions → agent finds relevant wiki pages (often starting from an **index**), reads them, answers **with citations**; valuable answers can be **filed back** into the wiki as new pages.
3. **Lint** — Periodic health check: contradictions, stale claims, orphans, missing pages, weak cross-refs, gaps (optionally suggesting new sources or searches).

### Navigation files (gist)

- **`index.md`** — Content catalog: links, one-line summaries, optional metadata; organized by category; updated on ingest; useful entry point before drilling into pages (works well at moderate scale without embeddings).
- **`log.md`** — Append-only chronological record (ingests, queries, lint). Prefer parseable entry headers (e.g. `## [2026-04-02] ingest | Article Title`) for simple tooling (`grep`, `tail`).

### Optional tooling (gist)

At larger scale: local search over wiki markdown (e.g. hybrid keyword + vector tools, MCP, or a small CLI). Until then, a maintained `index.md` may suffice.

---

## 2. How this maps to Wingman Edge

**Obsidian** is the intended viewer for vault markdown; the backend implements **automation** around the same three-layer mental model:

- **Raw layer in vault:** `{OBSIDIAN_VAULT_PATH}/raw/<topic>/…` — immutable-ish capture of source material (see ingest below).
- **Wiki layer:** `{OBSIDIAN_VAULT_PATH}/wiki/` — LLM-authored compiled notes as **flat** `wiki/<slug>.md` files (no subfolders under `wiki/`), plus `wiki/index.md` and `wiki/log.md`. Cross-structure is via **wikilinks**, not directories (not the same tree as `raw/`).
- **Schema (planned):** a single doc the agent loads for conventions (could live in the vault root or under `docs/` in the repo; this file describes intent until a vault-local schema exists).

---

## 3. Current implementation (through **ingest → raw vault → wiki compile**)

Ingest stores immutable captures under `raw/`, then (when the vault path is set) a **wiki compile agent** updates the compiled wiki under `wiki/` (articles, `index.md`, append to `log.md`).

### 3.1 LangGraph workflow

- **Graph builder:** `backend/wingman_edge_agents/workflows/wiki_graph.py`
  - `START` → `query_router` → conditional:
    - `ingest` → `ingest_fetch` → `ingest_compile` → `END`
    - `query` → `END` (stub: no wiki query node yet)
    - `lint` → `END` (stub: no lint node yet)

### 3.2 Router (`ingest` | `query` | `lint`)

- **Node:** `backend/wingman_edge_agents/graph/wiki_router.py`
- **Model:** structured output `QueryRouterOutput` (`action`, `query`) in `backend/wingman_edge_agents/graph/data_models.py`
- **Prompts:** `backend/wingman_edge_agents/agents/prompts/wiki_pompt.py` (`QUERY_ROUTER_SYS_PROMPT`)
- **Test override:** if `WIKI_VERIFY_INGEST` is `1` / `true` / `yes`, the router **forces** `ingest` (used by `workflows/main.py` smoke script).

### 3.3 Ingest nodes: raw capture then wiki compile

- **Nodes:** `backend/wingman_edge_agents/graph/wiki_nodes.py`
  - **`ingest_fetch`:** extract → topic placement → build markdown → save under `raw/` only; fills `WikiState` fields needed for compile (`data_source`, `ingest_output_path`, `ingest_*` metadata).
  - **`ingest_compile`:** `ensure_wiki_scaffold`, `NodeAgent.wiki_agent`, optional `ensure_wiki_fallback_article`; updates flat `wiki/*.md`, `index.md`, `log.md`.

### 3.3a Raw capture (`ingest_fetch`)

- **Node:** `ingest_fetch` in `wiki_nodes.py`
- **Extraction** (`backend/wingman_edge_agents/utils/wiki_utils.py`):
  - Local file via `file_path` / resolved path from query
  - HTTP(S) URL via Playwright (optional Obsidian Web Clipper extension env vars for clipping)
  - Otherwise treats `query` as inline text
- **Topic placement:** `NodeAgent.topic_agent` in `backend/wingman_edge_agents/agents/wiki_agent.py` — LangChain agent uses **read-only** vault tools to inspect existing `raw/` topics, then returns `TopicPlacementDecision` (`topic_directory`, `note_title`, optional `published_date`).
- **Tools for placement:** `backend/wingman_edge_agents/tools/vault_raw_tools.py` (`list_raw_topic_directories`, `list_files_in_raw_topic`, `read_head_of_raw_topic_note`).
- **Persistence:** `backend/wingman_edge_agents/utils/ingest_save.py`
  - `build_ingest_markdown` wraps body with title + source/collected/published metadata
  - `save_to_obsidian_raw` writes under `{vault}/raw/{topic_directory}/{optional-date-prefix}-{slug}.md` with collision-safe names

### 3.4 Wiki compile (`ingest_compile`)

- **Trigger:** LangGraph edge `ingest_fetch` → `ingest_compile` after each ingest route run when `OBSIDIAN_VAULT_PATH` is set and a raw path was written (otherwise compile no-ops with a skipped JSON in `wiki_generation`).
- **Scaffold:** `ensure_wiki_scaffold` in `backend/wingman_edge_agents/tools/vault_wiki_tools.py` ensures `wiki/`, `wiki/index.md`, and `wiki/log.md` exist (idempotent).
- **Agent:** `NodeAgent.wiki_agent` in `backend/wingman_edge_agents/agents/wiki_agent.py` — LangChain `create_agent` with tools from `vault_wiki_tools.py` (list articles, **read_wiki_file** for any `wiki/*.md` including `index.md`/`log.md`, write article / index / append log). Does **not** write to `raw/`. Shared path/read helpers live in `tools/root_fs.py`.
- **Prompt:** `WIKI_COMPILE_AGENT_SYS_PROMPT` in `backend/wingman_edge_agents/agents/prompts/wiki_pompt.py`.
- **Obsidian conventions** (generated markdown should be valid in Obsidian):
  - **Internal links:** [Obsidian — Links](https://obsidian.md/help/links) — use vault-relative **wikilinks** `[[path/without/extension]]` (and `[[path|alias]]`) for all in-vault targets between wiki pages and to raw sources; use ordinary markdown links only for external URLs.
  - **Tags:** [Obsidian — Tags](https://obsidian.md/help/tags) — topic articles include YAML `tags:` (e.g. `wiki`, `wiki/ingest`, `wiki/topic/<topic>`) plus inline `#wiki` (see prompt for the exact checklist).
- **State:** `WikiState.wiki_generation` holds a JSON summary string from the compile step (or an error object as JSON). `WikiState.generation` includes the raw path line and the wiki summary.
- **Fallback:** if the LLM completes but no flat `wiki/<slug>.md` article exists yet, `ensure_wiki_fallback_article` in `backend/wingman_edge_agents/utils/wiki_ingest_fallback.py` writes a minimal stub at `wiki/<slug>-ingest-wiki.md` (Obsidian wikilinks + tags) and appends `log.md`.

### 3.5 Environment variables

| Variable | Purpose |
|----------|---------|
| `OBSIDIAN_VAULT_PATH` | Absolute path to the Obsidian vault root. If unset, ingest still builds in-memory document but **does not** write disk (`generation` message explains). |
| `OBSIDIAN_WEB_CLIPPER_EXTENSION_PATH` | Optional: unpacked Web Clipper for Playwright path (see `wiki_utils.py`). |
| `OBSIDIAN_CLIPPER_HOTKEYS` | Optional: comma-separated clipper hotkeys. |
| `ROUTER_LLM`, `TOPIC_AGENT_LLM`, `DEFAULT_OLLAMA_MODEL` | Ollama models for router / topic agent (see `wiki_agent.py`). |
| `WIKI_INGEST_MODEL` | Default Ollama model for topic placement ingest agent (`NodeAgent.topic_agent`). |
| `WIKI_WIKI_AGENT_LLM` | Model for wiki compile agent (`NodeAgent.wiki_agent`); falls back to `WIKI_INGEST_MODEL`. |
| `WIKI_COMPILE_BODY_MAX_CHARS` | Max size of ingest body passed into the wiki compile prompt (default large cap; truncates with a notice). |
| `WIKI_VERIFY_INGEST` | Force ingest route for verification scripts. |

### 3.6 Local smoke / verification

- `backend/wingman_edge_agents/workflows/main.py` — runs the compiled graph for file + URL ingest cases; asserts new `.md` under `{vault}/raw/`, **no subfolders** under `wiki/`, flat wiki articles with wikilinks/`#wiki`, and `wiki/index.md` containing wikilinks to at least one `wiki/<stem>`.

---

## 4. What is **not** implemented yet (backlog aligned with the gist)

Implement the following in order that makes sense for your releases; each item should eventually be reflected in code **and** in this doc.

### 4.1 Wiki layer (remaining depth)

- **Done (ingest path):** `wiki/` tree, topic articles, `index.md` / `log.md` updates driven by `NodeAgent.wiki_agent` after each raw save (Obsidian wikilinks + tags per prompt).
- **Still open:** stronger **cascade** guarantees (deterministic ripple updates), richer entity/concept modeling, and contradiction handling beyond LLM judgment in the prompt.

### 4.2 `index.md` and `log.md` (hardening)

- **Done on ingest:** agent is instructed to rewrite `index.md` and append `log.md` on each successful compile.
- **Still open:** deterministic validation (parse tables vs on-disk files), query/lint-driven updates, and machine-grep hygiene checks in code—not only via the LLM.

### 4.3 Query operation (graph stub today)

- **Node:** read `index.md` (or search), open relevant wiki pages, synthesize answer with **citations** (paths or wikilinks).
- **Filing:** optional step to write the answer (or a distilled version) back as a new wiki page so exploration compounds.

### 4.4 Lint operation (graph stub today)

- Implement checks suggested in the gist: orphans, stale vs newer sources, missing entity pages, broken links, contradictions.
- Can start as a single LLM pass with a structured checklist, then harden with deterministic link parsing.

### 4.5 Schema document

- Add a dedicated **vault or repo** file (e.g. `WIKI.md` in vault, or extend this repo doc) that states: directory layout, naming, wikilink rules, frontmatter (if any), ingest/query/lint checklists.
- Agent prompts should **inject or reference** that schema so behavior is stable across sessions.

### 4.6 API / product surface

- Wire `build_wiki_graph()` into FastAPI (or Telegram) with clear request/response models: ingest payload (URL, file path, pasted text), query string, lint triggers.
- Respect auth and path safety if vault paths ever come from users.

### 4.7 Optional: search / MCP

- If `index.md` stops scaling, add local search (BM25/vector) or MCP tools over `wiki/` only, keeping `raw/` read-oriented for provenance.

---

## 5. Implementation principles (for agents)

1. **Preserve raw immutability:** do not overwrite existing raw notes in place; new captures use `allocate_unique_filename` semantics (or append-only raw policy if you change convention—document it).
2. **Keep tools least-privilege:** raw exploration tools are read-only; wiki writes should use separate, explicit write helpers with path validation (mirror `vault_raw_tools.py` patterns).
3. **Single source of truth:** when behavior or layout changes, update **this file** and the vault schema doc together.
4. **Match existing stack:** LangGraph state (`WikiState`), `RouterAgents` (router) and `NodeAgent` (ingest sub-agents), `LLMClient`, Ollama defaults, `backend.` import style—see `.cursor/rules/wingman-edge.mdc`.

---

## 6. Quick reference — key files

| Concern | Path |
|---------|------|
| Graph topology | `backend/wingman_edge_agents/workflows/wiki_graph.py` |
| Router node | `backend/wingman_edge_agents/graph/wiki_router.py` |
| Ingest nodes (`ingest_fetch`, `ingest_compile`) | `backend/wingman_edge_agents/graph/wiki_nodes.py` |
| State / DTOs | `backend/wingman_edge_agents/graph/data_models.py` |
| Raw save helpers | `backend/wingman_edge_agents/utils/ingest_save.py` |
| Extract file / URL | `backend/wingman_edge_agents/utils/wiki_utils.py` |
| Router + ingest agents | `backend/wingman_edge_agents/agents/wiki_agent.py` |
| Router / ingest / wiki compile prompts | `backend/wingman_edge_agents/agents/prompts/wiki_pompt.py` |
| Read-only raw tools | `backend/wingman_edge_agents/tools/vault_raw_tools.py` |
| Wiki read/write tools | `backend/wingman_edge_agents/tools/vault_wiki_tools.py` |
| Shared vault path + read/write primitives | `backend/wingman_edge_agents/tools/root_fs.py` |
| Generic + workspace-scoped file tools | `backend/wingman_edge_agents/tools/file_tools.py` (`init_workspace_root`, `read_workspace_file`, …) |
| Wiki ingest fallback stub | `backend/wingman_edge_agents/utils/wiki_ingest_fallback.py` |
| Smoke runner | `backend/wingman_edge_agents/workflows/main.py` |

---

## 7. Changelog (maintainers)

| Date | Note |
|------|------|
| 2026-04-11 | Initial spec: gist summary, repo mapping, ingest-complete milestone, backlog for wiki/query/lint/index/log/schema. |
| 2026-04-11 | Wiki compile after ingest: `wiki/` tools, `NodeAgent.wiki_agent`, Obsidian wikilinks + tags in compile prompt; smoke asserts on wiki output. |
