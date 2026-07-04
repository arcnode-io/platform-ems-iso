#!/bin/bash
# Bench bootstrap — run ONCE against a freshly-installed appliance that still
# has network (at our facility, before it ships airgapped). Installs ansible,
# drops the stack layer at /opt/arcnode, then hands convergence to systemd.
# After this the box self-converges every boot with no control node.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

apt-get update
apt-get install -y ansible-core rsync

install -d /opt/arcnode
rsync -a "$REPO/ansible/" /opt/arcnode/ansible/
install -m 0644 "$REPO/cfg.yml" /opt/arcnode/cfg.yml

# Airgap: install the vendored collection from the repo, never from galaxy.
ansible-galaxy collection install /opt/arcnode/ansible/collections/*.tar.gz --force

install -m 0644 "$REPO/install/arcnode.service" /etc/systemd/system/arcnode.service
systemctl daemon-reload
systemctl enable --now arcnode.service
