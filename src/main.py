"""uvicorn entry — HTTPS on 443 when TLS files exist, else HTTP on 80 for first boot.

Operator never runs this directly; systemd's arcnode-wizard.service does.
Bind to 0.0.0.0 so the LAN can reach the wizard before nginx is up.
"""

from __future__ import annotations

import logging
from pathlib import Path

import uvicorn

from src import config
from src.app import create_app

TLS_CERT = Path("/etc/arcnode/tls/server.crt")
TLS_KEY = Path("/etc/arcnode/tls/server.key")


def main() -> None:
    """Boot the wizard — HTTPS on 443 if TLS files exist, HTTP on 80 otherwise."""
    cfg = config.load_config()
    config.setup_logger(cfg)
    log = logging.getLogger(__name__)

    app = create_app()

    if TLS_CERT.exists() and TLS_KEY.exists():
        log.info("starting wizard on https://0.0.0.0:443 (TLS)")
        uvicorn.run(app, host="0.0.0.0", port=443,  # noqa: S104 — appliance must be LAN-reachable
                    ssl_keyfile=str(TLS_KEY), ssl_certfile=str(TLS_CERT))
    else:
        # First boot: no TLS yet — operator hits http://<appliance>/ and uploads
        # or self-signs cert during the TLS step. Wizard restarts itself with
        # HTTPS after apply.
        log.info("starting wizard on http://0.0.0.0:80 (no TLS — first boot)")
        uvicorn.run(app, host="0.0.0.0", port=80)  # noqa: S104


if __name__ == "__main__":
    main()
