"""Unit tests for the apply_stream orchestrator generator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.ai_models import AiModels
from src.apply_stream import apply_stream
from src.models import AdminLogin, ApplyRequest, TlsConfig

_FAKE_PW = "longenoughpw"


def _req() -> ApplyRequest:
    return ApplyRequest(
        tls=TlsConfig(mode="self_signed"),
        admin=AdminLogin(password=_FAKE_PW),
    )


def _fake_pull(_model: str) -> list[dict]:
    """Pretend ollama pull: manifest → 1 download tick → success."""
    return [
        {"status": "pulling manifest"},
        {"status": "downloading", "digest": "sha:1", "total": 100, "completed": 50},
        {"status": "success"},
    ]


def test_apply_stream_emits_phases_in_order(tmp_path: Path) -> None:
    # Arrange — patch write_secrets/write_tls/mark_setup_complete + subprocess
    models = AiModels(chat="a:1", code="b:2", embedder="c:3")

    with (
        patch("src.apply.write_secrets") as ws,
        patch("src.apply.write_tls") as wt,
        patch("src.apply.mark_setup_complete") as msc,
        patch("src.apply_stream.subprocess.Popen") as popen,
    ):
        popen.return_value.stdout = iter(["Pulling hivemq...\n", "Pull complete\n"])
        popen.return_value.wait.return_value = 0

        # Act
        events = list(
            apply_stream(_req(), models, pull_fn=_fake_pull, compose_dir=tmp_path)
        )

    # Assert — every phase opens and closes, in order
    phases_seen = [(e["phase"], e["status"]) for e in events if "status" in e]
    assert ("config", "start") in phases_seen
    assert ("config", "done") in phases_seen
    assert ("models", "start") in phases_seen
    assert ("models", "done") in phases_seen
    assert ("images", "start") in phases_seen
    assert ("images", "done") in phases_seen
    assert events[-1] == {"phase": "done", "redirect": "/"}

    # Side-effects fired
    ws.assert_called_once_with("longenoughpw")
    wt.assert_called_once()
    msc.assert_called_once()


def test_apply_stream_emits_one_model_progress_per_role(tmp_path: Path) -> None:
    # Arrange
    models = AiModels(chat="a:1", code="b:2", embedder="c:3")

    with (
        patch("src.apply.write_secrets"),
        patch("src.apply.write_tls"),
        patch("src.apply.mark_setup_complete"),
        patch("src.apply_stream.subprocess.Popen") as popen,
    ):
        popen.return_value.stdout = iter([])
        popen.return_value.wait.return_value = 0

        # Act
        events = list(
            apply_stream(_req(), models, pull_fn=_fake_pull, compose_dir=tmp_path)
        )

    # Assert — one model_start + one model_done per role
    starts = [
        e
        for e in events
        if e.get("phase") == "models" and e.get("status") == "model_start"
    ]
    dones = [
        e
        for e in events
        if e.get("phase") == "models" and e.get("status") == "model_done"
    ]
    assert [s["role"] for s in starts] == ["chat", "code", "embedder"]
    assert [d["role"] for d in dones] == ["chat", "code", "embedder"]


def test_apply_stream_raises_on_docker_pull_failure(tmp_path: Path) -> None:
    # Arrange — docker compose pull returns non-zero
    models = AiModels(chat="a:1", code="b:2", embedder="c:3")

    with (
        patch("src.apply.write_secrets"),
        patch("src.apply.write_tls"),
        patch("src.apply.mark_setup_complete"),
        patch("src.apply_stream.subprocess.Popen") as popen,
    ):
        popen.return_value.stdout = iter(["Error: network unreachable\n"])
        popen.return_value.wait.return_value = 1

        # Act — consume up to the error
        gen = apply_stream(_req(), models, pull_fn=_fake_pull, compose_dir=tmp_path)
        with pytest.raises(RuntimeError, match="rc=1"):
            list(gen)
