"""Integration tests: boot the built ISO in qemu-kvm, drive the wizard.

Skipped unless ARCNODE_ISO_PATH is set. CI's publish stage exports it after
`lb build` succeeds; locally you set it by hand for ad-hoc runs.
"""

from __future__ import annotations

import httpx

from tests.iso_fixtures import booted_iso, iso_path  # pytest fixture imports


def test_wizard_serves_setup_identity(booted_iso: str) -> None:
    """Identity endpoint round-trips the baked install.json contents."""
    # Act
    resp = httpx.get(f"{booted_iso}/setup/identity", timeout=10.0)

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    for key in ("customer", "site", "market", "isoVersion", "orderId"):
        assert key in body, f"identity payload missing {key}: {body}"


def test_wizard_root_renders_html_with_identity_inlined(booted_iso: str) -> None:
    """GET / serves the Jinja template with window.INSTALL_IDENTITY + HARDWARE_DATA inlined."""
    # Act
    resp = httpx.get(f"{booted_iso}/", timeout=10.0)

    # Assert
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "window.INSTALL_IDENTITY" in resp.text
    assert "window.HARDWARE_DATA" in resp.text


def test_hardware_endpoint_returns_real_probe(booted_iso: str) -> None:
    """GET /setup/hardware reports real host stats — overallStatus reflects qemu VM."""
    # Act
    resp = httpx.get(f"{booted_iso}/setup/hardware", timeout=10.0)

    # Assert — qemu defaults (2 cores, 4GB) will fail vs. our 8c/32GB min;
    # we're not asserting the verdict, just that the contract is honored.
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "cores",
        "ramBytes",
        "diskBytes",
        "nicMbps",
        "overallStatus",
    }
    assert body["overallStatus"] in {"ok", "warn", "fail"}


def test_wizard_apply_accepts_valid_payload(booted_iso: str) -> None:
    """POST /setup/apply with a valid payload returns 200 + redirect.

    Doesn't assert side effects on the appliance (writing /etc/arcnode/* +
    kicking arcnode-compose) — those need root inspection inside the VM.
    Asserting the HTTP contract is the integration-test scope.
    """
    # Arrange
    payload = {
        "apiKeys": [],
        "tls": {"mode": "self_signed"},
        "admin": {"username": "admin", "password": "demo-password-1"},
    }

    # Act
    resp = httpx.post(f"{booted_iso}/setup/apply", json=payload, timeout=60.0)

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "redirect" in body
