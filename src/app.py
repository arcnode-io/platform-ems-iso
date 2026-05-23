"""FastAPI app for the first-boot wizard.

Three routes:
  GET  /                — renders setup.html (or 410 if already complete)
  GET  /setup/identity  — returns the baked InstallIdentity as JSON
  POST /setup/apply     — applies the operator's submitted config
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import apply, identity
from src.models import ApplyRequest, ApplyResult

WIZARD_DIR = Path(__file__).resolve().parent.parent / "wizard"
TEMPLATES_DIR = WIZARD_DIR / "templates"
STATIC_DIR = WIZARD_DIR / "static"


def create_app(
    *,
    identity_path: Path = identity.DEFAULT_IDENTITY_PATH,
    setup_marker: Path = apply.SETUP_COMPLETE_MARKER,
    apply_fn: Callable[[ApplyRequest], None] = apply.apply_all,
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
        return templates.TemplateResponse(
            request,
            "setup.html",
            {"identity": ident.model_dump(by_alias=True)},
        )

    @app.get("/setup/identity")
    def get_identity() -> JSONResponse:
        _guard_complete()
        ident = identity.read_identity(identity_path)
        return JSONResponse(ident.model_dump(by_alias=True))

    @app.post("/setup/apply")
    def post_apply(req: ApplyRequest) -> ApplyResult:
        _guard_complete()
        apply_fn(req)
        # Redirect to / so the operator hits the 410 + the systemd unit can
        # tear the wizard down. nginx on the HMI takes over from there.
        return ApplyResult(ok=True, redirect="/")

    return app
