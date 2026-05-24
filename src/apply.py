"""Apply the wizard's submitted config to the appliance filesystem.

Writes:
  - /etc/arcnode/secrets.env       (API keys + admin creds)
  - /etc/arcnode/tls/server.{crt,key} (uploaded cert OR generated self-signed)
  - /var/lib/arcnode/setup-complete (marker — disables the wizard on next boot)

Then `systemctl start arcnode-compose.service` to hand off to the
long-running unit. Service-up wait is left to systemd's healthchecks.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from src.models import ApiKey, ApplyRequest, TlsConfig

ETC_DIR = Path("/etc/arcnode")
TLS_DIR = ETC_DIR / "tls"
SECRETS_PATH = ETC_DIR / "secrets.env"
SETUP_COMPLETE_MARKER = Path("/var/lib/arcnode/setup-complete")
# Env-var name per API key id. Drives what the apps read.
API_KEY_ENV_NAMES: dict[str, str] = {
    "openweathermap": "OPENWEATHERMAP_API_KEY",
    "gridstatus": "GRIDSTATUS_API_KEY",
}


def write_secrets(
    api_keys: list[ApiKey],
    admin_password: str,
    target: Path = SECRETS_PATH,
) -> None:
    """Render API keys + admin pw into the appliance secrets.env file.

    Format: KEY=value, one per line. compose's env_file directive reads
    this file at container start; same shape as cloud variants.
    """
    lines: list[str] = []
    for key in api_keys:
        env = API_KEY_ENV_NAMES.get(key.id)
        if env is None or key.skipped or not key.value:
            continue
        lines.append(f"{env}={key.value}")
    lines.append(f"GF_ADMIN_PASSWORD={admin_password}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n")
    target.chmod(0o600)


def write_tls(tls: TlsConfig, target_dir: Path = TLS_DIR) -> None:
    """Land the TLS cert + key on disk for the HMI's nginx/Caddy front.

    `upload` mode writes the operator-supplied pair. `self_signed` mode
    generates an openssl self-signed pair scoped to the appliance's
    hostname — browser warns, operator accepts, replaces from HMI later.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    if tls.mode == "upload":
        if not tls.cert_pem or not tls.key_pem:
            raise ValueError("upload mode requires both cert_pem and key_pem")
        (target_dir / "server.crt").write_text(tls.cert_pem)
        (target_dir / "server.key").write_text(tls.key_pem)
    else:
        # Self-signed via openssl — 365d cert, RSA 2048, CN matches the
        # appliance hostname so the browser warning is informational not
        # blocking. Operator replaces with a real cert from HMI settings.
        subprocess.run(  # noqa: S603 — fixed argv, no shell
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "365",
                "-keyout",
                str(target_dir / "server.key"),
                "-out",
                str(target_dir / "server.crt"),
                "-subj",
                "/CN=arcnode.local",
            ],
            check=True,
        )
    (target_dir / "server.key").chmod(0o600)
    (target_dir / "server.crt").chmod(0o644)


def kick_compose_unit() -> bool:
    """Trigger systemd's arcnode-compose.service via systemctl.

    Returns True if systemctl reported success, False otherwise. Caller
    decides whether a failure aborts the apply pipeline. Reason: under
    constrained hardware (qemu integration test, or a customer host
    that's tight on RAM), one of the data daemons (postgres-timeseries
    OOMs, neo4j slow-starts) may not be Active yet when arcnode-compose
    fires — its Requires=docker.service After=postgresql@15-... ordering
    means systemctl start returns non-zero. That's an appliance-runtime
    concern, not a wizard-contract failure. systemd will retry or the
    operator can reboot.
    """
    result = subprocess.run(
        ["systemctl", "start", "arcnode-compose.service"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logging.warning(
            "systemctl start arcnode-compose.service failed (rc=%d). "
            "Wizard apply will still succeed; operator should investigate. "
            "stderr=%s",
            result.returncode,
            result.stderr.strip()[:500],
        )
    return result.returncode == 0


def mark_setup_complete(marker: Path = SETUP_COMPLETE_MARKER) -> None:
    """Marker file so the wizard service refuses on the next boot."""
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(datetime.now(UTC).isoformat())


def is_setup_complete(marker: Path = SETUP_COMPLETE_MARKER) -> bool:
    """True iff the setup-complete marker exists — wizard refuses past this point."""
    return marker.exists()


def apply_all(req: ApplyRequest) -> None:
    """Full apply pipeline — write everything, mark done, hand off to systemd.

    kick_compose_unit failures are warn-and-continue: the wizard's
    contract is config-on-disk + marker, not "compose stack is live."
    Operator sees the warning in journalctl + can `systemctl start
    arcnode-compose` manually after fixing the underlying issue.
    """
    write_secrets(req.api_keys, req.admin.password)
    write_tls(req.tls)
    # Marker BEFORE the systemctl call — arcnode-compose has
    # ConditionPathExists=setup-complete so systemd would skip it otherwise.
    mark_setup_complete()
    kick_compose_unit()
