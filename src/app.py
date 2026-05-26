"""FastAPI app for the first-boot wizard.

Three routes:
  GET  /                — renders setup.html (or 410 if already complete)
  GET  /setup/identity  — returns the baked InstallIdentity as JSON
  POST /setup/apply     — applies the operator's submitted config
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import ai_models, apply, apply_stream, hardware, identity
from src.models import ApplyRequest

WIZARD_DIR = Path(__file__).resolve().parent.parent / "wizard"
TEMPLATES_DIR = WIZARD_DIR / "templates"
STATIC_DIR = WIZARD_DIR / "static"


def create_app(
    *,
    identity_path: Path = identity.DEFAULT_IDENTITY_PATH,
    setup_marker: Path = apply.SETUP_COMPLETE_MARKER,
    stream_fn: Callable[..., Iterator[dict]] = apply_stream.apply_stream,
    models_fn: Callable[[], ai_models.AiModels] = ai_models.load_ai_models,
    exit_after_apply: bool = True,
) -> FastAPI:
    """Wire the wizard routes. DI'd so tests can swap paths + the apply pipeline."""
    app = FastAPI(title="ARCNODE Setup Wizard")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _guard_complete() -> None:
        # Reason: once the marker exists the wizard MUST refuse — re-running
        # setup would clobber the live secrets file and bounce all services.
        if apply.is_setup_complete(setup_marker):
            raise HTTPException(status_code=410, detail="setup already complete")

    @app.get("/", response_class=HTMLResponse)
    def root(request: Request) -> HTMLResponse:
        _guard_complete()
        ident = identity.read_identity(identity_path)
        hw = hardware.probe()
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "identity": ident.model_dump(by_alias=True),
                "hardware": hw.model_dump(by_alias=True),
            },
        )

    @app.get("/setup/identity")
    def get_identity() -> JSONResponse:
        _guard_complete()
        ident = identity.read_identity(identity_path)
        return JSONResponse(ident.model_dump(by_alias=True))

    @app.get("/setup/hardware")
    def get_hardware() -> JSONResponse:
        # Reason: re-probed per call so the JSX's "Re-check" button gets
        # fresh data after the operator yanks a stick of RAM or whatever.
        _guard_complete()
        return JSONResponse(hardware.probe().model_dump(by_alias=True))

    @app.post("/setup/apply")
    def post_apply(req: ApplyRequest) -> StreamingResponse:
        _guard_complete()
        return _stream_apply(req, stream_fn, models_fn, exit_after_apply)

    return app


def _stream_apply(
    req: ApplyRequest,
    stream_fn: Callable[..., Iterator[dict]],
    models_fn: Callable[[], ai_models.AiModels],
    exit_after_apply: bool,
) -> StreamingResponse:
    """SSE stream of apply progress.

    Frontend reads via fetch + ReadableStream (NOT EventSource —
    EventSource is GET-only and we need the JSON body for pydantic
    validation). Each event = one `data: <json>\\n\\n` frame.
    """
    models = models_fn()

    def event_source() -> Iterator[bytes]:
        try:
            for ev in stream_fn(req, models):
                yield f"data: {json.dumps(ev)}\n\n".encode()
        except Exception as exc:
            logging.exception("apply_stream failed")
            err = json.dumps({"phase": "error", "message": str(exc)})
            yield f"data: {err}\n\n".encode()
            return
        if exit_after_apply:
            # 2s delay so the final SSE frame flushes before SIGTERM
            # tears the connection down. ExecStopPost then runs
            # arcnode-compose.service with port 80 free.
            threading.Thread(
                target=_shutdown_after,
                args=(2.0,),
                daemon=True,
            ).start()

    return StreamingResponse(event_source(), media_type="text/event-stream")


def _shutdown_after(delay_s: float) -> None:
    """Sleep then SIGTERM self — releases port 80 for HMI takeover."""
    time.sleep(delay_s)
    os.kill(os.getpid(), signal.SIGTERM)
