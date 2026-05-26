"""Stream-progress wrappers around the ollama pull API.

Used by the wizard apply pipeline to surface live byte-level progress to
the operator. Each call yields PullEvent dicts ready to SSE out.

Ollama's POST /api/pull returns NDJSON (one JSON object per line):
  {"status":"pulling manifest"}
  {"status":"downloading","digest":"...","total":17000000000,"completed":1234567}
  ...
  {"status":"success"}
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import TypedDict

import httpx

OLLAMA_URL = "http://127.0.0.1:11434"


class PullEvent(TypedDict, total=False):
    """One progress tick from `ollama pull`. All fields optional except status."""

    status: str  # e.g. "downloading" | "success" | "pulling manifest"
    digest: str
    total: int
    completed: int


def pull_ollama_model(
    model: str,
    *,
    base_url: str = OLLAMA_URL,
    timeout_s: float = 30.0,
) -> Iterator[PullEvent]:
    """Stream `ollama pull <model>` progress events from the daemon.

    Yields one PullEvent per NDJSON line. Caller decides what to do
    (forward as SSE, log, accumulate). Pull is idempotent — re-running
    on an already-cached model returns success quickly.
    """
    with httpx.stream(
        "POST",
        f"{base_url}/api/pull",
        json={"model": model, "stream": True},
        timeout=httpx.Timeout(timeout_s, read=None),
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            yield json.loads(line)
