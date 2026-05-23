# platform-ems-iso 🏭💿

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/platform-ems-iso?branch=main&logo=gitlab)
![](https://gitlab.com/arcnode-io/platform-ems-iso/badges/main/coverage.svg)
![](https://img.shields.io/badge/3.13.2-gray?logo=python)
![](https://img.shields.io/badge/ty_checked-gray?logo=astral)
![](https://img.shields.io/badge/0.10.9-gray?logo=uv)

On-prem appliance ISO for ARCNODE EMS — Debian base + systemd-managed
data daemons (postgres ×3, neo4j, minio, ollama) + dockerized app
services + a first-boot web wizard.

## Shape

- **`live-build/`** — debian live-build config; produces the bootable `.iso`.
- **`appliance/`** — what gets baked in:
  - `systemd/` — unit files for the data daemons.
  - `compose/` — app-services compose bundle (ISO variant, points at localhost daemons).
  - `first-boot/` — systemd service that starts the wizard on first boot.
- **`wizard/`** — FastAPI app for first-boot configuration (API keys, TLS, admin login).

## Build modes

1. **Reference build** (CI on `main`): defaults config, lands at
   `s3://arcnode-artifacts/iso/reference/`. Regression-tests the pipeline.
2. **Per-customer build** (API-triggered by `platform-api` on customer
   order): bakes the customer's ConfiguratorPayload + DTM, lands at
   `s3://arcnode-artifacts/iso/customers/{order_id}/`. Portal hands the
   customer a presigned download URL.

Both run on the dev runner at 173.211.12.43 (see
`engineering-with-ai/tooling-playbooks`).

## Related

- [`platform-api`](https://gitlab.com/arcnode-io/platform-api) — orchestrates customer ISO builds + portal delivery.
- [`ems`](https://gitlab.com/arcnode-io/ems) — system ADR + deployment diagrams.
