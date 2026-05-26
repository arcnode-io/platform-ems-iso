"""End-to-end integration: spin a real app via TestClient, walk all routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app


def test_first_boot_walks_identity_to_apply(tmp_path: Path) -> None:
    """Wizard binds /, /setup/identity, /setup/apply with no setup marker."""
    # Arrange — baked install.json + no marker
    identity = tmp_path / "install.json"
    identity.write_text(
        json.dumps(
            {
                "customer": "Acme",
                "site": "Site-A",
                "market": "ERCOT · HB_NORTH",
                "isoVersion": "1.0.0",
                "isoBuiltAt": "23 May 2026",
                "orderId": "test",
                "rev": "Rev 1",
            }
        )
    )
    marker = tmp_path / "setup-complete"
    app = create_app(
        identity_path=identity,
        setup_marker=marker,
        apply_fn=lambda _: None,  # don't actually touch disk + systemd
        exit_after_apply=False,  # don't kill the test process
    )
    client = TestClient(app)

    # Act + Assert — home page renders, identity round-trips, apply succeeds
    home = client.get("/")
    assert home.status_code == 200
    assert "window.INSTALL_IDENTITY" in home.text
    assert "window.HARDWARE_DATA" in home.text

    ident = client.get("/setup/identity").json()
    assert ident["customer"] == "Acme"

    hw = client.get("/setup/hardware").json()
    assert "overallStatus" in hw

    apply_resp = client.post(
        "/setup/apply",
        json={
            "tls": {"mode": "self_signed"},
            "admin": {"password": "long-enough-pw"},
        },
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json() == {"ok": True, "redirect": "/"}
