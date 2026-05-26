"""Integration tests: boot the built ISO in qemu-kvm, drive the wizard.

Skipped unless ARCNODE_ISO_PATH is set. CI's publish stage exports it after
`lb build` succeeds; locally you set it by hand for ad-hoc runs.
"""

from __future__ import annotations

import json

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
    """POST /setup/apply with a valid payload streams a text/event-stream.

    Apply runs ollama-pull + docker-compose-pull inside qemu where neither
    is available; the stream will yield a `phase: error` frame. That's
    fine — this test asserts the HTTP contract (endpoint accepts the
    payload + streams SSE), not the success of the apply pipeline. End-
    to-end success lives in the real-hardware install test.
    """
    # Arrange
    payload = {
        "tls": {"mode": "self_signed"},
        "admin": {"password": "demo-password-1"},
    }

    # Act
    resp = httpx.post(f"{booted_iso}/setup/apply", json=payload, timeout=120.0)

    # Assert
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    frames = [f for f in resp.text.split("\n\n") if f.startswith("data: ")]
    assert len(frames) >= 1
    # First frame is the config-start event — proves the stream started
    first = json.loads(frames[0][len("data: ") :])
    assert first["phase"] == "config"
