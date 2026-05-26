"""Streaming-progress orchestrator for the wizard apply pipeline.

Wraps apply.write_secrets + write_tls + ollama pulls + docker compose
pulls into a single generator that yields SSE-ready dict events. The
FastAPI route serializes each event as a `data:` SSE frame.

Phases (in order, mostly serial — docker + ollama could parallelize
later if total apply time is a pain point):
  config  → write secrets + TLS
  models  → pull each ai_models.{chat,code,embedder} via ollama daemon
  images  → docker compose pull (stream raw stdout lines)
  done    → mark setup-complete, emit redirect

Compose service kick still happens via systemd ExecStopPost on
arcnode-wizard.service — apply_stream just marks done and returns,
wizard shuts down 2s later, ExecStopPost fires, compose binds port 80.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src import apply
from src.ai_models import AiModels
from src.download import pull_ollama_model
from src.models import ApplyRequest

StreamEvent = dict[str, Any]


def apply_stream(
    req: ApplyRequest,
    models: AiModels,
    *,
    compose_dir: Path = Path("/etc/arcnode/compose"),
    pull_fn: Any = pull_ollama_model,  # noqa: ANN401 — generator type wide
) -> Iterator[StreamEvent]:
    """Yield progress events through the whole apply pipeline.

    Caller forwards each event as an SSE frame. Pure generator; raises
    on hard failures (operator must retry). Ollama + docker pulls are
    idempotent — re-running picks up where it left off.
    """
    # Phase 1 — config
    yield {"phase": "config", "status": "start"}
    apply.write_secrets(req.admin.password)
    apply.write_tls(req.tls)
    yield {"phase": "config", "status": "done"}

    # Phase 2 — pull ai models, one role at a time
    role_models = [
        ("chat", models.chat),
        ("code", models.code),
        ("embedder", models.embedder),
    ]
    yield {
        "phase": "models",
        "status": "start",
        "roles": [{"role": r, "model": m} for r, m in role_models],
    }
    for role, model in role_models:
        yield {"phase": "models", "status": "model_start", "role": role, "model": model}
        for ev in pull_fn(model):
            yield {
                "phase": "models",
                "status": "model_progress",
                "role": role,
                "model": model,
                "ollama": ev,
            }
        yield {"phase": "models", "status": "model_done", "role": role, "model": model}
    yield {"phase": "models", "status": "done"}

    # Phase 3 — docker compose pull. Stream raw stdout per line.
    yield {"phase": "images", "status": "start"}
    proc = subprocess.Popen(
        ["docker", "compose", "pull"],
        cwd=str(compose_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip()
        if line:
            yield {"phase": "images", "status": "log", "line": line}
    rc = proc.wait()
    if rc != 0:
        yield {"phase": "images", "status": "error", "returncode": rc}
        raise RuntimeError(f"docker compose pull failed with rc={rc}")
    yield {"phase": "images", "status": "done"}

    # Phase 4 — mark setup-complete + emit redirect.
    # Compose service kick happens in systemd ExecStopPost after wizard exits.
    apply.mark_setup_complete()
    yield {"phase": "done", "redirect": "/"}
