# ARCNODE Appliance 📦

> Stock Debian, laid down by Hetzner `installimage`. The stack (daemons, DBs,
> broker, HMI) is laid down and kept converged by **Ansible running on the box
> itself** — no control node, so it keeps working behind the customer firewall.

## History

This repo used to master a custom Debian live/installer ISO (live-build +
GRUB + preseed + d-i). Weeks of firmware-class debugging over the telephone
taught the lesson: **the install medium was our biggest bug surface and it
wasn't the product.** That approach is preserved at the git tag
`archive/live-build-approach`.

The appliance is now a **plain Debian install** plus an Ansible self-converge
layer. Each capability is added in an increment provable on real hardware first.

## Walking skeleton

| step | capability | proof |
|---|---|---|
| 1 | login greeting | ssh in → the MOTD says `arcnode` |
| 2 | ansible self-converge → docker → one container | reboot → `curl localhost` says `arcnode`; re-run play = `changed=0` |
| … | (grow the compose one daemon at a time — DBs, broker, HMI) | |

## Architecture

Two clean seams:

- **installimage lays the OS.** Stock Debian 12, RAID1, hostname `arcnode`,
  login greeting. Nothing else. (`install/arcnode.conf` + `install/postinstall.sh`.)
- **Ansible lays the stack.** `ansible/site.yml` runs *on the box*
  (`connection: local`) — installs docker, renders the compose from `cfg.yml`,
  brings it up. A systemd unit (`install/arcnode.service`) re-runs it every
  boot, so the box self-converges with no control node reachable. This is why
  Ansible over a bash script: idempotent day-2 convergence behind the firewall.

The **compose** (`ansible/compose.yml.j2`) is the shared artifact — same file
the cloud EC2 consumes; only the launcher differs (cloud UserData bash vs the
appliance's local Ansible). DBs on the appliance are **containers** in this
compose (airgap can't use managed Tiger/Aurora); the app talks to the generic
`TimeseriesClient` either way.

Config lives in `cfg.yml`. Secrets stay in env, never here.

## Provision

**1 — OS.** From the Hetzner **rescue system** (Robot → activate rescue → reset):

```sh
# copy the two files over, then:
installimage -a -c install/arcnode.conf -x install/postinstall.sh
reboot
```

**2 — Stack.** On the booted box, once, while it still has network (at our
facility, before it ships airgapped):

```sh
# with this repo checked out on the box:
sudo install/provision.sh
```

`provision.sh` is the only bash bootstrap: it installs `ansible-core`, copies
the stack layer to `/opt/arcnode`, installs the vendored `community.docker`
collection (from `ansible/collections/`, never galaxy — airgap), and enables
`arcnode.service`. From then on the box converges itself every boot.

> Not yet airgap-complete: `provision.sh` apt-installs ansible, and the first
> converge pulls docker packages + images over the network. Vendoring those
> (apt mirror / `.deb`s, `docker save`/`load` image bundle) is a later
> increment. The Ansible collection — the day-2 convergence dependency — is
> already vendored.
