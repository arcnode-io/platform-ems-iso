"""Read the baked install identity from /etc/arcnode/install.json.

The ISO build pipeline writes `install.json` per-customer at bake time
from the ConfiguratorPayload. The wizard's step-1 read-back uses this
to show the operator "you booted the right .iso for this order."
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models import InstallIdentity

DEFAULT_IDENTITY_PATH = Path("/etc/arcnode/install.json")


def read_identity(path: Path = DEFAULT_IDENTITY_PATH) -> InstallIdentity:
    """Parse the baked install.json. Fail loud if missing — the wizard
    can't run without it, and a missing file means the ISO was built wrong."""
    raw = json.loads(path.read_text())
    return InstallIdentity.model_validate(raw)
