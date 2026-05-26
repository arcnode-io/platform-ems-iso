"""FastAPI route tests using TestClient + DI'd paths."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.ai_models import AiModels
from src.app import create_app
from src.models import ApplyRequest


@pytest.fixture
def baked_identity(tmp_path: Path) -> Path:
    """Write a stand-in /etc/arcnode/install.json the wizard can read."""
    f = tmp_path / "install.json"
    f.write_text(
        json.dumps(
            {
                "customer": "Acme",
                "site": "Site-A",
                "market": "ERCOT · HB_NORTH",
                "isoVersion": "1.0.0",
                "isoBuiltAt": "29 Apr 2026",
                "orderId": "CFG-X",
                "rev": "Rev 1",
            }
        )
    )
    return f


@pytest.fixture
def marker(tmp_path: Path) -> Path:
    """Path the wizard checks for the setup-complete sentinel."""
    return tmp_path / "setup-complete"


def test_root_renders_setup_html_with_identity_inlined(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange
    app = create_app(
        identity_path=baked_identity, setup_marker=marker, exit_after_apply=False
    )
    client = TestClient(app)

    # Act
    resp = client.get("/")

    # Assert — identity + hardware both made it into the inline <script>
    assert resp.status_code == 200
    assert "window.INSTALL_IDENTITY" in resp.text
    assert "window.HARDWARE_DATA" in resp.text
    assert "Acme" in resp.text
    assert "isoVersion" in resp.text


def test_hardware_endpoint_returns_camelcase_report(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange
    app = create_app(
        identity_path=baked_identity, setup_marker=marker, exit_after_apply=False
    )
    client = TestClient(app)

    # Act
    resp = client.get("/setup/hardware")

    # Assert — wire shape matches HW_SCENARIOS in hardware-check.jsx
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "cores",
        "ramBytes",
        "diskBytes",
        "nicMbps",
        "overallStatus",
    }
    for row in ("cores", "ramBytes", "diskBytes", "nicMbps"):
        assert set(body[row].keys()) == {"detected", "min", "recommended", "status"}


def test_identity_endpoint_returns_camelcase_json(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange
    app = create_app(
        identity_path=baked_identity, setup_marker=marker, exit_after_apply=False
    )
    client = TestClient(app)

    # Act
    resp = client.get("/setup/identity")

    # Assert — camelCase out so the JSX field names match
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer"] == "Acme"
    assert body["isoVersion"] == "1.0.0"


def test_apply_streams_phase_events(baked_identity: Path, marker: Path) -> None:
    # Arrange — fake stream_fn so we don't actually pull ollama / docker
    def fake_stream(_req: ApplyRequest, _models: AiModels) -> Iterator[dict]:
        yield {"phase": "config", "status": "start"}
        yield {"phase": "config", "status": "done"}
        yield {"phase": "done", "redirect": "/"}

    def fake_models() -> AiModels:
        return AiModels(chat="a:1", code="b:2", embedder="c:3")

    app = create_app(
        identity_path=baked_identity,
        setup_marker=marker,
        stream_fn=fake_stream,
        models_fn=fake_models,
        exit_after_apply=False,
    )
    client = TestClient(app)
    payload = {
        "tls": {"mode": "self_signed", "certPem": None, "keyPem": None},
        "admin": {"password": "long-enough-pw"},
    }

    # Act
    resp = client.post("/setup/apply", json=payload)

    # Assert — SSE response carries the events as `data: <json>\n\n` frames
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    frames = [f for f in resp.text.split("\n\n") if f]
    assert len(frames) == 3
    assert '"phase": "config"' in frames[0]
    assert '"phase": "done"' in frames[-1]


def test_routes_return_410_when_setup_already_complete(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange — pre-create the marker; valid body so we're testing the guard, not validation
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("2026-05-22T00:00:00+00:00")
    app = create_app(
        identity_path=baked_identity, setup_marker=marker, exit_after_apply=False
    )
    client = TestClient(app)
    valid_apply = {
        "tls": {"mode": "self_signed"},
        "admin": {"password": "long-enough-pw"},
    }

    # Act + Assert — every route 410s; no path is reachable post-setup
    assert client.get("/").status_code == 410
    assert client.get("/setup/identity").status_code == 410
    assert client.get("/setup/hardware").status_code == 410
    assert client.post("/setup/apply", json=valid_apply).status_code == 410
