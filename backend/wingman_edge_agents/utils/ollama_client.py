"""
Ollama reachability + SDK helpers.

Debug: set env ``WINGMAN_DEBUG_OLLAMA=1`` (or ``true``) then watch backend logs, e.g.::

    docker compose logs -f backend

Stdout is line-buffered under Docker; ``flush=True`` keeps messages visible quickly.
"""

import logging
import os
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

import ollama
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Inside Docker: service name + container listen port (not host publish port).
_DEFAULT_OLLAMA = "http://ollama:11434"


def _ollama_debug_enabled() -> bool:
    return os.environ.get("WINGMAN_DEBUG_OLLAMA", "").lower() in ("1", "true", "yes")


def _dbg(msg: str) -> None:
    """Print to container stdout when WINGMAN_DEBUG_OLLAMA is set; also log at DEBUG."""
    line = f"[ollama_client] {msg}"
    logger.debug("%s", line)
    if _ollama_debug_enabled():
        print(line, flush=True)


def _ollama_http_base() -> str:
    raw = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA).strip().rstrip("/")
    if "://" not in raw:
        raw = "http://" + raw
    _dbg(f"OLLAMA_BASE_URL effective (HTTP): {raw!r} (env raw={os.environ.get('OLLAMA_BASE_URL')!r})")
    return raw


def _ollama_tcp_host_port() -> tuple[str, int]:
    parsed = urlparse(_ollama_http_base())
    host = parsed.hostname or "127.0.0.1"
    # Port inside Ollama container is always 11434 unless you customize the image.
    port = parsed.port or 11434
    _dbg(f"TCP probe target: host={host!r} port={port}")
    return host, port


def _ollama_sdk_client() -> ollama.Client:
    base = _ollama_http_base()
    _dbg(f"ollama.Client(host={base!r})")
    return ollama.Client(host=base)


def is_ollama_running(host: str | None = None, port: int | None = None) -> bool:
    """Check if the Ollama server is accepting TCP connections on the configured host."""
    if host is None or port is None:
        host, port = _ollama_tcp_host_port()
    try:
        with socket.create_connection((host, port), timeout=2.0):
            _dbg(f"TCP OK {host}:{port}")
            return True
    except OSError as e:
        _dbg(f"TCP FAIL {host}:{port} -> {e!r}")
        return False


def start_ollama():
    """Start Ollama in the background."""
    print("Starting Ollama server...")
    try:
        if os.name == "nt":  # Windows
            subprocess.Popen("start ollama serve", shell=True)
            return True
        subprocess.Popen(
            ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        sys.exit(1)


def list_ollama_models() -> list:
    """List available models in Ollama."""
    models_names: list[str] = []
    try:
        _dbg("calling ollama.Client.list() …")
        models = _ollama_sdk_client().list()["models"]
        _dbg(f"list() returned {len(models)} model(s)")
        if not models:
            print("⚠️ No models found. Please run: `ollama pull llama3` or similar.")
            return []
        print("📦 Available models:", models[0]["model"])

        for model in models:
            print(f"{model['model']}")
            models_names.append(model["model"])
        return models_names
    except Exception as e:
        print(f"Error listing models: {e}")
        _dbg(f"list() exception: {e!r}")
        return []


def wait_for_ollama(timeout=15):
    """Wait until Ollama is ready."""
    print("Waiting for Ollama to be ready...")
    for _ in range(timeout):
        if is_ollama_running():
            print("✅ Ollama is running.")
            models = list_ollama_models()
            print("Available models:", models)
            return True
        time.sleep(1)
    print("❌ Ollama did not start in time.")
    return False


def get_available_models():
    """Get a list of available models."""
    if not is_ollama_running():
        if not wait_for_ollama():
            print("❌ Failed to start Ollama.")
            return []
    return list_ollama_models()


""" Below is a fucntion to test for backend chatting, this is CLI """
