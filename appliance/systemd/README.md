# Appliance systemd units

Units we ship that aren't already in standard Debian packages.

| Unit | What it runs | Dep on |
|---|---|---|
| `arcnode-wizard.service` | FastAPI setup wizard (port 80 / 443) | network-online; skipped after `setup-complete` marker exists |
| `arcnode-compose.service` | `docker compose up -d` against `/etc/arcnode/compose/docker-compose.yaml` | docker + all data daemons + `setup-complete` marker |
| `minio.service` | MinIO server bound to `/opt/arcnode/minio/data` | network-online |
| `ollama.service` | Ollama runtime, models pre-baked at `/opt/arcnode/ollama/models` | network-online |

## What we DON'T ship a unit for

Debian's own packages provide these:

- **PostgreSQL** — `apt install postgresql-16 timescaledb-2-postgresql-16 postgresql-16-pgvector`.
  Three clusters created at first boot via `pg_createcluster 16 timeseries|document|vector`.
  Debian writes `postgresql@16-<cluster>.service` template units automatically.
- **Neo4j** — `apt install neo4j` writes `neo4j.service`.
- **Docker** — `apt install docker.io` writes `docker.service`.

## Boot order

```
network-online
  ├─ arcnode-wizard           (if !setup-complete)
  ├─ postgresql@16-timeseries
  ├─ postgresql@16-document
  ├─ postgresql@16-vector
  ├─ neo4j
  ├─ minio
  ├─ ollama
  └─ docker
        └─ arcnode-compose    (if setup-complete + secrets.env)
```

## Install

live-build hook copies these into `/etc/systemd/system/` and runs
`systemctl enable arcnode-wizard arcnode-compose minio ollama` in the chroot.
The wizard exits + drops the marker → next boot brings the app stack up.

The wizard's apply pipeline calls `systemctl start arcnode-compose.service`
itself (see `src/apply.py:kick_compose_unit`). Operator submits → marker
written → systemd kicks compose. Operator hits the HMI URL the wizard
returns. No power-cycle needed.
