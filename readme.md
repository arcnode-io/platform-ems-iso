# ARCNODE Appliance 📦

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/platform-ems-iso?branch=main&logo=gitlab)

> Plain Debian + one bootstrap script. No custom ISO.

## Approach

The previous incarnation of this repo mastered a custom Debian live/installer
ISO (live-build + GRUB surgery + preseed + d-i). Weeks of fighting
firmware-class bugs over the telephone taught the lesson: **the install medium
was our biggest bug surface and it wasn't our product.**

Reset (2026-07-02): the appliance is a **stock Debian install** — Hetzner
`installimage`, the official netinst ISO, whatever the hardware takes — plus
`bootstrap.sh` layered on top in verifiable increments. Each increment must be
provable on real hardware before the next lands.

The old approach is preserved at the git tag `archive/live-build-approach`
(wizard UI, appliance compose, UEFI qemu tests — cherry-pick when needed).

## Walking skeleton

| step | capability | proof |
|---|---|---|
| 1 | login banner | log in → see `arcnode` |
| … | (grow from here) | |

## Use

On a fresh Debian box, as root:

```sh
curl -fsSL https://arcnode-public.s3.amazonaws.com/appliance/bootstrap.sh | sh
```

Log out, log in: `arcnode`.

## Hetzner iteration loop

1. Rescue system → `installimage` → Debian 12 → reboot
2. SSH in, run the bootstrap
3. Verify the step's proof
