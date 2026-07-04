#!/bin/bash
# Pull every image the appliance compose references and save them to one airgap
# bundle + a sha256 manifest. Run at the bench (network up) before the box ships.
# The stack role loads this bundle before `compose up`, so first converge behind
# the customer firewall needs zero registry access.
set -euo pipefail
OUT=${1:-/opt/arcnode/images}
COMPOSE=${2:-/opt/arcnode/stack/compose.yml}
mkdir -p "$OUT"
# Image list comes straight from the rendered compose — never hand-maintained.
mapfile -t IMAGES < <(docker compose -f "$COMPOSE" config --images | sort -u)
echo "pulling ${#IMAGES[@]} images..."
for img in "${IMAGES[@]}"; do docker pull -q "$img"; done
echo "saving bundle..."
docker save "${IMAGES[@]}" -o "$OUT/bundle.tar"
sha256sum "$OUT/bundle.tar" | awk '{print $1}' > "$OUT/bundle.sha256"
printf '%s\n' "${IMAGES[@]}" > "$OUT/manifest.txt"
echo "bundled ${#IMAGES[@]} images → $OUT/bundle.tar ($(du -h "$OUT/bundle.tar" | cut -f1))"
