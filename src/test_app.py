"""FastAPI route tests using TestClient + DI'd paths."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.app import create_app


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
    app = create_app(identity_path=baked_identity, setup_marker=marker)
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
    app = create_app(identity_path=baked_identity, setup_marker=marker)
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
    app = create_app(identity_path=baked_identity, setup_marker=marker)
    client = TestClient(app)

    # Act
    resp = client.get("/setup/identity")

    # Assert — camelCase out so the JSX field names match
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer"] == "Acme"
    assert body["isoVersion"] == "1.0.0"


def test_apply_calls_pipeline_and_returns_redirect(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange — fake apply_fn so we don't actually touch /etc or docker
    fake_apply = MagicMock()
    app = create_app(
        identity_path=baked_identity, setup_marker=marker, apply_fn=fake_apply
    )
    client = TestClient(app)
    payload = {
        "apiKeys": [
            {"id": "openweathermap", "value": "k1", "skipped": False},
        ],
        "tls": {"mode": "self_signed", "certPem": None, "keyPem": None},
        "admin": {"username": "admin", "password": "long-enough-pw"},
    }

    # Act
    resp = client.post("/setup/apply", json=payload)

    # Assert
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "redirect": "/"}
    assert fake_apply.call_count == 1


def test_routes_return_410_when_setup_already_complete(
    baked_identity: Path, marker: Path
) -> None:
    # Arrange — pre-create the marker; valid body so we're testing the guard, not validation
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("2026-05-22T00:00:00+00:00")
    app = create_app(identity_path=baked_identity, setup_marker=marker)
    client = TestClient(app)
    valid_apply = {
        "apiKeys": [],
        "tls": {"mode": "self_signed"},
        "admin": {"username": "admin", "password": "long-enough-pw"},
    }

    # Act + Assert — every route 410s; no path is reachable post-setup
    assert client.get("/").status_code == 410
    assert client.get("/setup/identity").status_code == 410
    assert client.get("/setup/hardware").status_code == 410
    assert client.post("/setup/apply", json=valid_apply).status_code == 410
