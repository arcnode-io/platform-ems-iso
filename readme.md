# platform-ems-iso 🏭💿

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/platform-ems-iso?branch=main&logo=gitlab)
![](https://gitlab.com/arcnode-io/platform-ems-iso/badges/main/coverage.svg)
![](https://img.shields.io/badge/3.13.2-gray?logo=python)
![](https://img.shields.io/badge/ty_checked-gray?logo=astral)
![](https://img.shields.io/badge/0.10.9-gray?logo=uv)

On-prem appliance ISO for ARCNODE EMS — Debian Bookworm base + systemd-managed
data daemons (postgres ×3, neo4j, minio, ollama) + dockerized app services
+ a first-boot web wizard.

## System requirements

Minimum spec the appliance is sized for (single-host, single-site deployment):

| Resource | Minimum | Recommended | Why |
|---|---|---|---|
| CPU | 8 cores | 16 cores | postgres ×3 + neo4j + ollama + app stack |
| RAM | 32 GB | 64 GB | ollama models live in RAM; neo4j + postgres want headroom |
| Disk | 256 GB SSD | 1 TB NVMe | timeseries grows; ollama models ~20–30 GB baked |
| NIC | 1 Gbps | 10 Gbps | south-side device polling + HMI traffic |

Boots on bare metal, vSphere, KVM, or Proxmox. No GPU required —
ollama runs on CPU; latency budget is operator-tolerable.

## Shape

- **`live-build/`** — debian live-build config; produces the bootable `.iso`. [README](live-build/README.md)
- **`appliance/`** — what gets baked in:
  - `systemd/` — unit files for daemons + wizard + compose orchestration. [README](appliance/systemd/README.md)
  - `compose/` — app-services compose bundle (ISO variant, points at localhost daemons).
- **`wizard/`** — FastAPI app for first-boot configuration (API keys, TLS, admin login).
- **`src/`** — wizard backend (models, identity, apply, app, main).

## Build modes

| Mode | Trigger | Output | What's baked |
|---|---|---|---|
| **dev** | local maintainer `lb build` | local `.iso` | base + hooks 10/20/70/80 only — no model/image preload (fast iteration) |
| **release** | CI on `main` | `s3://arcnode-artifacts/iso/reference/` | everything including ollama models + docker images |
| **per-customer** | platform-api on order | `s3://arcnode-artifacts/iso/customers/{order_id}/` | release + per-customer `install.json` + `cfg.customer.yml` + DTM |

Both CI modes run on the dev runner at `173.211.12.43` (see
`engineering-with-ai/tooling-playbooks` for the ansible).

## First-boot flow

```
Debian installer (stock d-i)
  └─ user picks disk, sets hostname, reboots
       │
       ▼
First boot
  ├─ data daemons start (postgres ×3, neo4j, minio, ollama)
  └─ arcnode-wizard.service binds :80 (or :443 if TLS files exist)
       │
       ▼
Operator opens http://<appliance>/ in a browser
  ├─ Step 1 — identity readback (confirms right ISO for the order)
  ├─ Step 2 — API keys (OpenWeatherMap, gridstatus, NREL — optional/skippable)
  ├─ Step 3 — TLS (upload cert+key, or self-sign for now)
  ├─ Step 4 — admin login (HMI credentials)
  └─ Step 5 — review + apply
       │
       ▼
Wizard writes /etc/arcnode/secrets.env + TLS files + setup-complete marker
  └─ arcnode-compose.service fires (ConditionPathExists=/var/lib/arcnode/setup-complete)
       │
       ▼
App stack lives — operator points the browser at the HMI
```

The wizard refuses (`HTTP 410`) on second boot — it's first-boot-only by
design. Reconfiguration happens through the HMI settings.

## Local dev

```sh
uv sync
uv run pytest src/ -q       # 20 unit tests
uv run poe lint
uv run poe typecheck
uv run python -m src.main   # runs wizard on http://localhost:80 (needs sudo for port)
```

## Related

- [`platform-api`](https://gitlab.com/arcnode-io/platform-api) — orchestrates customer ISO builds + portal delivery.
- [`ems`](https://gitlab.com/arcnode-io/ems) — system ADR + deployment diagrams.
