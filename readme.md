# ARCNODE Appliance 📦

> Stock Debian, laid down by Hetzner `installimage`. The EMS stack (broker, DBs,
> gateway, HMI, analyst) is laid down and kept converged by **Ansible running on
> the box itself** — no control node, so it converges behind the customer
> firewall and re-converges every boot.

## History

This repo used to master a custom Debian live/installer ISO (live-build + GRUB +
preseed + d-i). Weeks of firmware-class debugging taught the lesson: **the
install medium was our biggest bug surface and it wasn't the product.** That
approach is preserved at the git tag `archive/live-build-approach`.

The appliance is now a **plain Debian install** plus an Ansible self-converge
layer. Each capability is an increment proved on real hardware before the next
lands.

## Walking skeleton

| step | capability | proof |
|---|---|---|
| 1 | login greeting | ssh in → MOTD says `arcnode` |
| 2 | ansible self-converge → docker → container | reboot → container back; re-run = `changed=0` |
| 3 | real EMS core: broker + DBs + gateway + mocks + writer | gateway → File-RBAC broker → Timescale hypertable (proven: 2105+ rows, 5 devices) |
| 4 | airgap image bundle | all images wiped + every registry blackholed → converge from bundle (proven: 12 containers up offline) |
| 5 | OS hardening | ufw active, ssh key-only, fail2ban banning (proven on box) |
| … | TLS ingress · analyst/HMI · observability | (in progress — see Roadmap) |

## Architecture

Two clean seams:

- **installimage lays the OS.** Stock Debian 12, RAID1, hostname `arcnode`,
  login greeting. Nothing else. (`install/arcnode.conf` + `install/postinstall.sh`.)
- **Ansible lays the stack.** `ansible/site.yml` runs *on the box*
  (`connection: local`), roles in order:
  - `base` — ufw / ssh hardening / fail2ban
  - `docker` — engine + compose plugin
  - `secrets` — generate every credential locally (persisted, idempotent) +
    render the File-RBAC `credentials.xml`
  - `config` — per-service `cfg.customer.yml` + the device topology (`dtm.json`)
  - `stack` — load the airgap image bundle, then `docker compose up`

  `install/arcnode.service` (oneshot systemd) re-runs the play every boot, so
  the box self-converges with no control node reachable. That day-2 idempotent
  convergence behind the firewall is why Ansible over a bash script.

The **compose** (`ansible/roles/stack/templates/compose.yml.j2`) is the shared
artifact — same topology the cloud EC2 consumes; only the launcher differs
(cloud UserData bash vs the appliance's local Ansible). Persistence on the
appliance is **local containers** (airgap can't reach managed Tiger/Aurora); the
app talks to the generic `TimeseriesClient` URL either way.

**Secrets** are generated on-box (`ansible/roles/secrets`, `password` lookup,
persisted under `/opt/arcnode/secrets`, 0700) — no AWS Secrets Manager, no setup
wizard. `credentials.xml` is byte-identical to the working platform-api
File-RBAC ACL (5 identities, 5 roles). Config lives in `cfg.yml`; secrets never do.

## Provision

**1 — OS.** From the Hetzner **rescue system** (Robot → activate rescue → reset):

```sh
installimage -a -c install/arcnode.conf -x install/postinstall.sh
reboot
```

**2 — Airgap bundle (at the bench, network up, before it ships).** After the OS
is provisioned and converged online once, snapshot every image:

```sh
sudo tools/bundle-images.sh          # → /opt/arcnode/images/bundle.tar + sha256
```

**3 — Stack.** On the booted box, once:

```sh
sudo install/provision.sh
```

`provision.sh` installs `ansible-core`, copies the stack layer to
`/opt/arcnode`, installs the **vendored** `community.docker` collection (from
`ansible/collections/`, never galaxy), and enables `arcnode.service`. From then
on the box converges itself every boot — offline, from the bundle.

## Day-2 ops

```sh
systemctl start arcnode.service                    # force a re-converge
journalctl -u arcnode.service -f                   # watch a converge
docker compose -f /opt/arcnode/stack/compose.yml ps    # stack state
sudo tools/factory-reset.sh                        # wipe data + secrets, re-converge fresh
```

## Airgap posture

| dependency | status |
|---|---|
| docker images | ✅ vendored — `bundle.tar`, loaded before compose up |
| `community.docker` ansible collection | ✅ vendored in `ansible/collections/` |
| apt packages (docker-ce, ansible-core) | ⏳ still pulled at bench provision (task: vendor `.debs`) |
| ollama models | ⏳ pending model-selection decision |

Provisioning happens at our bench with network; only the shipped, converged box
must run offline — and the image + collection layers already do.

## Roadmap (see the session task list)

TLS ingress (nginx-443 WSS) · analyst-server + ollama/neo4j/pgvector/minio (HMI
depends on analyst-server resolving; blocked on real Ollama model tags) ·
observability (prometheus/grafana/mlflow) · signed update bundles · release
manifest · apt `.deb` vendoring · molecule CI.
