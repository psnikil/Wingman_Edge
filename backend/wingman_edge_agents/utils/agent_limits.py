"""Shared wall-clock / HTTP budgets for ReAct-style agents."""

import os


def agent_max_seconds() -> float:
    """Max seconds for a single agent run (Ollama + tools). Default 300."""
    raw = os.getenv("WINGMAN_AGENT_MAX_SEC", "300")
    try:
        value = float(raw)
    except ValueError:
        return 300.0
    return max(1.0, value)
