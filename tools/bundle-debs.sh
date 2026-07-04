#!/bin/bash
# Download the full offline .deb closure (docker engine + compose + ansible-core
# + rsync + all deps) into $OUT, using a clean debian:12 container so the
# dependency resolution matches the ISO's base. Run at the bench (network up).
set -euo pipefail
OUT="${1:-/tmp/arcnode-iso/debs}"
mkdir -p "$OUT"
docker run --rm -v "$OUT:/debs" debian:12 bash -c '
  set -e
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg >/dev/null
  install -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y --download-only ansible-core rsync docker-ce docker-ce-cli containerd.io docker-compose-plugin >/dev/null
  cp /var/cache/apt/archives/*.deb /debs/
'
echo "deb closure: $(find "$OUT" -name "*.deb" | wc -l) packages, $(du -sh "$OUT" | cut -f1)"
