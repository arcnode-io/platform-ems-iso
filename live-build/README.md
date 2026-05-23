# debian live-build skeleton

Builds `arcnode-ems-<version>.iso` — a Debian Bookworm bootable installer
with the ARCNODE app stack pre-baked.

## Layout

```
live-build/
├── auto/
│   ├── config              # `lb config` defaults (bookworm, amd64, hybrid ISO)
│   ├── build               # `lb build` wrapper with logging
│   └── clean               # `lb clean --purge`
├── config/
│   ├── package-lists/
│   │   └── arcnode.list.chroot   # apt packages baked into the image
│   ├── hooks/live/
│   │   ├── 0010-create-users.hook.chroot          # minio-user, ollama users
│   │   ├── 0020-postgres-clusters.hook.chroot     # 3 clusters: timeseries/document/vector
│   │   ├── 0030-install-minio.hook.chroot         # unpinned-latest minio + mc (matches dev)
│   │   ├── 0040-install-ollama.hook.chroot        # unpinned-latest ollama (matches dev)
│   │   ├── 0050-preload-ollama-models.hook.chroot # bakes qwen3 + nomic-embed-text
│   │   ├── 0060-preload-docker-images.hook.chroot # pulls every image in compose file
│   │   ├── 0070-install-wizard.hook.chroot        # uv sync the FastAPI wizard venv
│   │   └── 0080-enable-services.hook.chroot       # systemctl enable units
│   └── includes.chroot/   # populated at build time, NOT in git
│       ├── etc/systemd/system/         # appliance/systemd/* copied here
│       ├── etc/arcnode/install.json    # per-customer identity (baked by platform-api)
│       ├── etc/arcnode/compose/        # appliance/compose/* copied here
│       └── opt/arcnode/wizard/         # this repo's src/ + pyproject + uv.lock
```

## MinIO + Ollama: unpinned-latest

Hooks 0030 + 0040 pull MinIO and Ollama from their official URLs at build
time, unpinned. Matches the dev-server pattern
(`tooling-playbooks/dev-services-setup.yml`) — what's in dev is what
ships. If we ever need bit-for-bit reproducibility, pin both with sha256
checks at that point.

## Building locally

```sh
sudo apt install live-build squashfs-tools xorriso
cd live-build
sudo lb config       # invokes auto/config
sudo lb build        # ~30 min on first run, ~10 min incremental
```

Output: `arcnode-ems-<version>.iso` in the build dir.

## Building in CI

The `gitlab-runner` on `173.211.12.43` (per `engineering-with-ai/tooling-playbooks`)
has the live-build packages + KVM access. CI invokes `auto/build` after
copying the per-customer `install.json` into `includes.chroot/etc/arcnode/`.

## Three build modes

| Mode | When | Includes |
|---|---|---|
| **dev** | local maintainer | base + hooks 0010/0020/0070/0080, no model preload |
| **release** | platform-api per-customer bake | everything, including model preload + image preload |
| **smoke** | CI per-MR | base + 0010/0020/0080, no preloads (fast) |

Mode selected via env var (TODO: wire `ARCNODE_BUILD_MODE` in auto/config).

## What's NOT in the skeleton yet

- `auto/config` archives block (Timescale repo, Neo4j repo, Docker repo apt sources)
- `includes.chroot` population logic — currently expected to be done by the CI job
- `preseed.cfg` for unattended Debian install step
- Per-customer overlay (the install.json + cfg.customer.yml that platform-api injects)
- `0030` and `0040` hooks pinned with checksums (operator action)
