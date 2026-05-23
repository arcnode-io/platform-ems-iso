"""Unit tests for identity.read_identity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.identity import read_identity


def test_reads_baked_install_json(tmp_path: Path) -> None:
    # Arrange — write a baked-style install.json
    f = tmp_path / "install.json"
    f.write_text(
        json.dumps(
            {
                "customer": "Acme",
                "site": "Site-A",
                "market": "ERCOT · HB_NORTH",
                "isoVersion": "1.0.0-rc1",
                "isoBuiltAt": "29 Apr 2026",
                "orderId": "CFG-X",
                "rev": "Rev 1",
            }
        )
    )

    # Act
    identity = read_identity(f)

    # Assert
    assert identity.customer == "Acme"
    assert identity.iso_version == "1.0.0-rc1"


def test_missing_file_raises(tmp_path: Path) -> None:
    # Arrange + Act + Assert — fail loud, the wizard can't proceed without it
    with pytest.raises(FileNotFoundError):
        read_identity(tmp_path / "missing.json")


def test_malformed_json_raises(tmp_path: Path) -> None:
    # Arrange
    f = tmp_path / "install.json"
    f.write_text("{not json")

    # Act + Assert
    with pytest.raises(json.JSONDecodeError):
        read_identity(f)
