"""Wiki ingestion helpers: local files (text / markdown / HTML / PDF OCR) and web via Playwright."""

from __future__ import annotations

import mimetypes
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import pymupdf4llm
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

load_dotenv()

_RAW_TEXT_SUFFIXES = {".txt", ".text", ".log", ".env", ".csv"}
_MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
_HTML_SUFFIXES = {".html", ".htm"}
_PDF_SUFFIXES = {".pdf"}

_URL_RE = re.compile(r"^https?://", re.I)


def is_http_url(value: str) -> bool:
    value = value.strip()
    if not value or not _URL_RE.match(value):
        return False
    try:
        u = urlparse(value)
        return bool(u.netloc)
    except Exception:
        return False


def resolve_ingest_path(query: str, file_path: str | None) -> Path | None:
    if file_path:
        p = Path(file_path).expanduser().resolve()
        if p.is_file():
            return p
    q = query.strip()
    if q and not is_http_url(q):
        p2 = Path(q).expanduser().resolve()
        if p2.is_file():
            return p2
    return None


def read_raw_text_bytes(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def html_string_to_markdown(html: str) -> str:
    print("html:", len(html))
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title_el = soup.title
    title = title_el.get_text(strip=True) if title_el else ""

    root = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body
    if root is None:
        root = soup

    parts: list[str] = []
    if title:
        parts.append(f"# {title}\n")

    for hx in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6"], recursive=True):
        level = int(hx.name[1])
        text = hx.get_text(" ", strip=True)
        if text:
            parts.append("#" * level + f" {text}\n")

    for para in root.find_all("p", recursive=True):
        text = para.get_text(" ", strip=True)
        if text:
            parts.append(text + "\n")

    for lst in root.find_all("ul", recursive=True):
        for li in lst.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True)
            if text:
                parts.append(f"- {text}\n")
        parts.append("")

    body_md = "\n".join(parts).strip()
    if len(body_md) < 80:
        body_md = root.get_text("\n\n", strip=True)
    return body_md


def extract_pdf_to_markdown(path: Path, engine: str = "pymupdf4llm") -> str:
    
    if engine == "pymupdf4llm":
        try:
            doc = pymupdf4llm.to_markdown(path)
        except Exception as e:
            return f"Error extracting PDF to markdown: {e}"
        return doc
    else:
        # TODO: Implement PDF extraction using ollama OCR model 
        return f"Error extracting PDF to markdown: {engine} engine not supported"
    # chunks: list[str] = [f"# {path.name}\n"]
    # try:
    #     for i in range(len(doc)):
    #         page = doc.load_page(i)
    #         chunks.append(f"\n## Page {i + 1}\n\n")
    #         try:
    #             tp = page.get_textpage_ocr(language="eng", dpi=300, full=True)
    #             chunks.append(str(tp.extractTEXT()))
    #         except RuntimeError:
    #             chunks.append(str(page.get_text("text")))
    # finally:
    #     doc.close()
    # return "".join(chunks).strip()


def ingest_from_path(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in _PDF_SUFFIXES:
        return extract_pdf_to_markdown(path)
    if suf in _RAW_TEXT_SUFFIXES:
        return read_raw_text_bytes(path)
    if suf in _MARKDOWN_SUFFIXES:
        return read_raw_text_bytes(path)
    if suf in _HTML_SUFFIXES:
        return html_string_to_markdown(read_raw_text_bytes(path))
    mime, _ = mimetypes.guess_type(str(path))
    if mime == "text/plain":
        return read_raw_text_bytes(path)
    return f"[unsupported file type: {path.suffix or mime or 'unknown'}]\n"


def _clipper_chromium_args(ext_dir: str) -> list[str]:
    ext_dir = str(Path(ext_dir).resolve())
    return [
        f"--disable-extensions-except={ext_dir}",
        f"--load-extension={ext_dir}",
    ]


def _extension_has_manifest(ext: str) -> bool:
    p = Path(ext).resolve()
    return p.is_dir() and (p / "manifest.json").is_file()


def extract_url_with_playwright(url: str) -> str:
    """
    Load a URL with Playwright. If OBSIDIAN_WEB_CLIPPER_EXTENSION_PATH is set to an unpacked
    Chromium extension directory containing manifest.json, launch a persistent context with that
    extension (non-headless), fire optional hotkeys, then try the page clipboard. Otherwise use
    a headless browser and convert the DOM to markdown.

    Env:
    - OBSIDIAN_WEB_CLIPPER_EXTENSION_PATH: path to unpacked Obsidian Web Clipper (Chromium build)
    - OBSIDIAN_CLIPPER_HOTKEYS: comma-separated shortcuts, default Alt+Shift+O,Control+Shift+O
    - WIKI_PLAYWRIGHT_USER_DATA: optional persistent user-data dir for clipper profile
    """
    ext = os.environ.get("OBSIDIAN_WEB_CLIPPER_EXTENSION_PATH", "").strip()
    hotkeys = [
        h.strip()
        for h in os.environ.get(
            "OBSIDIAN_CLIPPER_HOTKEYS",
            "Alt+Shift+O,Control+Shift+O",
        ).split(",")
        if h.strip()
    ]

    user_data = os.environ.get("WIKI_PLAYWRIGHT_USER_DATA", "").strip()
    if not user_data:
        user_data = tempfile.mkdtemp(prefix="wiki_playwright_")

    note = ""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else url

    with sync_playwright() as p:
        browser = None
        context = None
        try:
            if ext and _extension_has_manifest(ext):
                try:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data,
                        headless=False,
                        args=_clipper_chromium_args(ext),
                        ignore_default_args=["--disable-extensions"],
                    )
                except Exception:
                    context = None
                    note = "(Could not start headed browser with Obsidian Web Clipper; using headless HTML extraction.)\n\n"

            if context is None:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()

            page = context.pages[0] if context.pages else context.new_page()
            try:
                context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
            except Exception:
                pass

            page.goto(url, wait_until="domcontentloaded", timeout=60_000)

            clipped = ""
            print('note:', note)
            print('ext:', ext)
            print('hotkeys:', hotkeys)
            if ext and hotkeys and note == "":
                for combo in hotkeys:
                    try:
                        page.keyboard.press(combo)
                        page.wait_for_timeout(1500)
                        clipped = page.evaluate(
                            """async () => {
                                try { return await navigator.clipboard.readText(); }
                                catch (e) { return ''; }
                            }"""
                        )
                        if isinstance(clipped, str) and len(clipped.strip()) > 200:
                            break
                    except Exception:
                        continue

            # if isinstance(clipped, str) and clipped.strip():
            #     print("clipped:", clipped)
            #     body = note + clipped.strip()
            # else:
            body = note + html_string_to_markdown(page.content())
            print("page",body)
            context.close()
            context = None
            if browser is not None:
                browser.close()
                browser = None

            return f"# Clipped from `{url}`\n\n{body}"

        except Exception as e:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            return f"# Error loading `{url}`\n\n```\n{e!r}\n```"


def resolve_ingest_source_label(query: str, file_path: str | None) -> str:
    path = resolve_ingest_path(query, file_path)
    if path is not None:
        return f"file:{path}"
    if is_http_url(query):
        return f"url:{query.strip()}"
    return "inline_or_unknown"
