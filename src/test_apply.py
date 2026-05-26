"""Unit tests for apply.* — file writes only, no subprocess calls."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.apply import (
    is_setup_complete,
    kick_compose_unit,
    mark_setup_complete,
    write_secrets,
    write_tls,
)
from src.models import TlsConfig


def test_write_secrets_writes_admin_password(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "secrets.env"

    # Act
    write_secrets("adminpw", target=target)

    # Assert
    content = target.read_text()
    assert content.strip() == "GF_ADMIN_PASSWORD=adminpw"
    # Reason: secrets.env carries plaintext creds — must be 0600 not world-readable
    assert (target.stat().st_mode & 0o777) == 0o600


def test_write_tls_upload_writes_both_pem(tmp_path: Path) -> None:
    # Arrange
    tls = TlsConfig(mode="upload", cert_pem="cert-bytes", key_pem="key-bytes")

    # Act
    write_tls(tls, target_dir=tmp_path)

    # Assert
    assert (tmp_path / "server.crt").read_text() == "cert-bytes"
    assert (tmp_path / "server.key").read_text() == "key-bytes"
    # Reason: private key must not be world-readable
    assert (tmp_path / "server.key").stat().st_mode & 0o777 == 0o600


def test_write_tls_upload_rejects_missing_pem(tmp_path: Path) -> None:
    # Arrange + Act + Assert — both halves required in upload mode
    tls = TlsConfig(mode="upload", cert_pem="cert", key_pem=None)
    with pytest.raises(ValueError, match="cert_pem and key_pem"):
        write_tls(tls, target_dir=tmp_path)


def test_write_tls_self_signed_calls_openssl(tmp_path: Path) -> None:
    # Arrange — patch subprocess so we don't shell out in the unit test
    tls = TlsConfig(mode="self_signed")

    with patch("src.apply.subprocess.run") as run:
        # The patched call doesn't write files, so the chmod step would
        # fail — pre-create the files so the chmod succeeds + we can
        # verify the openssl argv.
        (tmp_path / "server.crt").write_text("")
        (tmp_path / "server.key").write_text("")

        # Act
        write_tls(tls, target_dir=tmp_path)

    # Assert — openssl invoked with the expected argv shape
    args = run.call_args.args[0]
    assert args[0] == "openssl"
    assert "req" in args and "-x509" in args


def test_kick_compose_unit_calls_systemctl_start() -> None:
    # Arrange + Act
    with patch("src.apply.subprocess.run") as run:
        run.return_value.returncode = 0
        ok = kick_compose_unit()

    # Assert — exact systemctl argv shape + reports success
    args = run.call_args.args[0]
    assert args == ["systemctl", "start", "arcnode-compose.service"]
    assert ok is True


def test_kick_compose_unit_returns_false_on_nonzero_exit() -> None:
    # Arrange + Act — systemctl failure must not raise; caller decides
    with patch("src.apply.subprocess.run") as run:
        run.return_value.returncode = 1
        run.return_value.stderr = "Failed to start unit"
        ok = kick_compose_unit()

    # Assert
    assert ok is False


def test_setup_complete_marker_round_trip(tmp_path: Path) -> None:
    # Arrange
    marker = tmp_path / "setup-complete"
    assert not is_setup_complete(marker)

    # Act
    mark_setup_complete(marker)

    # Assert
    assert is_setup_complete(marker)
    # Marker carries a timestamp for forensics
    assert marker.read_text().endswith("+00:00")
