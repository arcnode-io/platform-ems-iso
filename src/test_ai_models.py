"""Unit tests for the role→model mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ai_models import AiModels, load_ai_models


def test_load_ai_models_parses_three_roles(tmp_path: Path) -> None:
    # Arrange
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "ai_models:\n" "  chat: foo:1\n" "  code: bar:2\n" "  embedder: baz:3\n",
    )

    # Act
    models = load_ai_models(cfg)

    # Assert
    assert models.chat == "foo:1"
    assert models.code == "bar:2"
    assert models.embedder == "baz:3"


def test_load_ai_models_rejects_missing_role(tmp_path: Path) -> None:
    # Arrange — missing 'embedder' must fail loud; appliance can't run
    # without all three downstream consumers.
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("ai_models:\n  chat: a\n  code: b\n")

    # Act + Assert
    with pytest.raises(ValueError, match="embedder"):
        load_ai_models(cfg)


def test_repo_cfg_yml_loads_cleanly() -> None:
    # Arrange + Act — the shipped cfg.yml must parse + populate all roles
    models = load_ai_models()

    # Assert
    assert isinstance(models, AiModels)
    assert ":" in models.chat  # version tag present
    assert ":" in models.code
