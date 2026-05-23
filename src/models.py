"""Pydantic models for the first-boot wizard request/response shapes.

Mirrors the contract the designer's wizard JSX expects:
  - GET  /setup/identity → InstallIdentity (read-only, baked at build)
  - POST /setup/apply    → ApplyRequest in, ApplyResult out

Keep field names matching the JSX (lowerCamelCase) so the JSON wire
contract doesn't need translation on either side.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    head, *tail = s.split("_")
    return head + "".join(t.capitalize() for t in tail)


class _Wire(BaseModel):
    """Base — camelCase JSON, snake_case Python, strict ignore."""

    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        extra="forbid",
    )


class InstallIdentity(_Wire):
    """Read-only identity baked at ISO build time. Shown on wizard step 1."""

    customer: str
    site: str
    market: str
    iso_version: str
    iso_built_at: str
    order_id: str
    rev: str


class ApiKey(_Wire):
    """One API-key field from the wizard's API-keys step."""

    id: str                              # 'openweathermap' | 'gridstatus' | ...
    value: str | None = None             # secret material; None if skipped
    skipped: bool = False


class TlsConfig(_Wire):
    """Wizard's TLS step result."""

    mode: str = Field(pattern="^(self_signed|upload)$")
    cert_pem: str | None = None          # only when mode='upload'
    key_pem: str | None = None           # only when mode='upload'


class AdminLogin(_Wire):
    """HMI admin credentials chosen at the wizard's final step."""

    username: str = Field(min_length=1)
    password: str = Field(min_length=8)   # strength meter is client-side advice


class ApplyRequest(_Wire):
    """Full POST /setup/apply body."""

    api_keys: list[ApiKey]
    tls: TlsConfig
    admin: AdminLogin


class ApplyResult(_Wire):
    """POST /setup/apply success response."""

    ok: bool = True
    redirect: str = "/"                  # where to send the operator after success
