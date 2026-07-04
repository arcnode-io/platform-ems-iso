#!/bin/bash
# Apply a signed appliance update on an airgapped box. An operator drops
# update.tar + update.tar.sig at /opt/arcnode/updates. We verify the signature
# against the baked public key BEFORE touching anything, then load the new
# images + refreshed ansible and re-converge. A tampered or unsigned bundle is
# rejected and nothing changes.
set -euo pipefail
UPD=${1:-/opt/arcnode/updates}
PUB=${2:-/opt/arcnode/keys/update.pub}
tar="$UPD/update.tar"; sig="$UPD/update.tar.sig"
[ -f "$tar" ] && [ -f "$sig" ] || { echo "no update bundle at $UPD"; exit 1; }
echo "verifying signature against $PUB ..."
if ! openssl pkeyutl -verify -pubin -inkey "$PUB" -rawin -in "$tar" -sigfile "$sig" >/dev/null 2>&1; then
  echo "SIGNATURE INVALID — refusing to apply"; exit 1
fi
echo "signature OK — applying"
work=$(mktemp -d); tar -xf "$tar" -C "$work"
# refreshed ansible + image bundle ride inside update.tar
[ -d "$work/ansible" ] && rsync -a --delete "$work/ansible/" /opt/arcnode/ansible/
[ -f "$work/bundle.tar" ] && install -D -m0644 "$work/bundle.tar" /opt/arcnode/images/bundle.tar
rm -rf "$work"
systemctl start arcnode.service
echo "update applied + re-converged"
