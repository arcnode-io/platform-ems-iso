"""Unit tests for wire-model camelCase round-trip + validation."""

from __future__ import annotations

import pytest

from src.models import (
    AdminLogin,
    ApplyRequest,
    InstallIdentity,
    TlsConfig,
)


def test_install_identity_round_trip() -> None:
    # Arrange — JSON shape matches the designer's INSTALL_IDENTITY mock
    body = {
        "customer": "Brookside Energy LLC",
        "site": "Brookside DC-1",
        "market": "ERCOT · Houston Hub",
        "isoVersion": "arcnode-ems-1.0.0",
        "isoBuiltAt": "29 Apr 2026",
        "orderId": "CFG-2026-0142",
        "rev": "Rev 3",
    }

    # Act
    parsed = InstallIdentity.model_validate(body)
    serialized = parsed.model_dump(by_alias=True)

    # Assert
    assert parsed.iso_version == "arcnode-ems-1.0.0"
    assert serialized == body  # camelCase round-trips


def test_apply_request_round_trips() -> None:
    # Arrange
    body = {
        "tls": {"mode": "self_signed"},
        "admin": {"password": "longenoughpw"},
    }

    # Act
    req = ApplyRequest.model_validate(body)

    # Assert
    assert req.tls.mode == "self_signed"
    pw = "longenoughpw"
    assert req.admin.password == pw


def test_admin_password_min_length_enforced() -> None:
    # Arrange + Act + Assert — pydantic raises on <8 char password
    with pytest.raises(ValueError, match="at least 8"):
        AdminLogin.model_validate({"password": "short"})


def test_tls_mode_rejects_unknown() -> None:
    # Arrange + Act + Assert — only self_signed | upload allowed
    with pytest.raises(ValueError, match="pattern"):
        TlsConfig.model_validate({"mode": "magic"})


def test_apply_request_rejects_extra_fields() -> None:
    # Arrange — strict ignore=forbid: extra keys raise rather than silently drop
    body = {
        "tls": {"mode": "self_signed"},
        "admin": {"password": "longenoughpw"},
        "rogue": "field",
    }

    # Act + Assert
    with pytest.raises(ValueError, match="rogue"):
        ApplyRequest.model_validate(body)
