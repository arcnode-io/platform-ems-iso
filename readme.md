# ARCNODE Appliance 📦

> Stock Debian. No custom ISO. Provisioned with Hetzner `installimage`; the
> only customization is the login greeting.

## History

This repo used to master a custom Debian live/installer ISO (live-build +
GRUB + preseed + d-i). Weeks of firmware-class debugging over the telephone
taught the lesson: **the install medium was our biggest bug surface and it
wasn't the product.** That approach is preserved at the git tag
`archive/live-build-approach`.

The appliance is now a **plain Debian install** plus a post-install hook.
Each capability is added in an increment provable on real hardware first.

## Walking skeleton

| step | capability | proof |
|---|---|---|
| 1 | login greeting | ssh in → the MOTD says `arcnode` |
| … | (grow from here) | |

## Provision (Hetzner dedicated)

From the Hetzner **rescue system** (Robot → activate rescue → reset):

```sh
# copy the two files over, then:
installimage -a -c install/arcnode.conf -x install/postinstall.sh
reboot
```

`arcnode.conf` installs stock Debian 12 (RAID1 across the two NVMe, hostname
`arcnode`). `postinstall.sh` runs in the installed chroot and sets
`/etc/motd` to `arcnode`. First login greets you.
