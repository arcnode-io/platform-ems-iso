"""Role → model mapping for the ollama models the appliance ships.

Roles (chat / code / embedder) stay stable; model versions can swap
without touching wizard UI or consumer code. cfg.yml owns the mapping.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class AiModels(BaseModel):
    """One model per agent role. All three pulled during wizard apply."""

    chat: str
    code: str
    embedder: str


DEFAULT_CFG_PATH = Path("cfg.yml")


def load_ai_models(path: Path = DEFAULT_CFG_PATH) -> AiModels:
    """Parse the `ai_models:` block from cfg.yml."""
    data = yaml.safe_load(path.read_text())
    return AiModels(**data["ai_models"])
