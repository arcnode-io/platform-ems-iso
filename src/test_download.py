"""Unit tests for the ollama pull stream wrapper.

Tests use httpx's MockTransport to fake the ollama daemon — no real
http://127.0.0.1:11434 needed.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from src.download import pull_ollama_model


def _mock_transport(ndjson_lines: list[dict]) -> httpx.MockTransport:
    """Build a MockTransport that replies with the given ndjson lines."""
    body = "\n".join(json.dumps(line) for line in ndjson_lines) + "\n"

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


def test_pull_emits_each_ndjson_line() -> None:
    # Arrange — synthetic ollama pull stream: manifest → 2 downloads → success
    lines = [
        {"status": "pulling manifest"},
        {"status": "downloading", "digest": "sha256:a", "total": 100, "completed": 50},
        {"status": "downloading", "digest": "sha256:a", "total": 100, "completed": 100},
        {"status": "success"},
    ]
    transport = _mock_transport(lines)

    # Act
    with patch("src.download.httpx.stream") as stream:
        stream.return_value.__enter__.return_value = httpx.Client(
            transport=transport,
        ).send(httpx.Request("POST", "http://x/api/pull"), stream=True)
        events = list(pull_ollama_model("qwen3:30b-a3b"))

    # Assert — every NDJSON line surfaces as a PullEvent
    assert len(events) == 4
    assert events[0]["status"] == "pulling manifest"
    assert events[1]["completed"] == 50
    assert events[-1]["status"] == "success"


def test_pull_raises_on_non_200() -> None:
    # Arrange — daemon returns 404 (model name typo)
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    transport = httpx.MockTransport(handler)

    # Act + Assert
    with (
        patch("src.download.httpx.stream") as stream,
        pytest.raises(httpx.HTTPStatusError),
    ):
        stream.return_value.__enter__.return_value = httpx.Client(
            transport=transport,
        ).send(httpx.Request("POST", "http://x/api/pull"), stream=True)
        list(pull_ollama_model("bogus"))
