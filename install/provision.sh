#!/bin/bash
# First-boot bootstrap. Runs OFFLINE from the ISO payload: installs docker +
# ansible + rsync from debs baked into the payload (dpkg — no apt mirror), drops
# the stack layer at /opt/arcnode, installs the vendored collection, and hands
# convergence to systemd. The box then self-converges every boot with no network.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Offline base packages: docker engine + compose plugin + ansible-core + rsync.
# dpkg from the baked closure; a bench run (network up) can still apt-fix.
if ls "$REPO"/debs/*.deb >/dev/null 2>&1; then
  dpkg -i "$REPO"/debs/*.deb 2>/dev/null || dpkg --configure -a || true
fi

install -d /opt/arcnode/ansible
cp -a "$REPO/ansible/." /opt/arcnode/ansible/
install -m 0644 "$REPO/cfg.yml" /opt/arcnode/cfg.yml

# airgap image bundle → where the stack role loads it before compose up
if ls "$REPO"/images/*.tar >/dev/null 2>&1; then
  install -d /opt/arcnode/images
  cp "$REPO"/images/*.tar /opt/arcnode/images/
fi

# Vendored collection (airgap — never galaxy).
ansible-galaxy collection install /opt/arcnode/ansible/collections/*.tar.gz -p /opt/arcnode/ansible/vendored_collections --force

install -m 0644 "$REPO/install/arcnode.service" /etc/systemd/system/arcnode.service
systemctl daemon-reload
systemctl enable arcnode.service
systemctl start arcnode.service || true
