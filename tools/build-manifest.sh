#!/bin/bash
# Emit an auditable manifest of the appliance's exact composition: ansible
# commit, every image ref + content id, and the bundle checksum. Run at the
# bench after bundle-images.sh. A box's manifest answers "what is running here".
set -euo pipefail
OUT=${1:-/opt/arcnode}
COMPOSE=${2:-/opt/arcnode/stack/compose.yml}
VERSION=${3:-dev}          # pass git describe from the bench; no clock in-script
commit=$(git -C "$(dirname "$0")/.." rev-parse HEAD 2>/dev/null || echo unknown)
{
  echo "{"
  echo "  \"appliance_version\": \"$VERSION\","
  echo "  \"ansible_commit\": \"$commit\","
  if [ -f "$OUT/images/bundle.sha256" ]; then
    echo "  \"bundle_sha256\": \"$(cat "$OUT/images/bundle.sha256")\","
  fi
  echo "  \"images\": ["
  docker compose -f "$COMPOSE" config --images | sort -u | while read -r ref; do
    id=$(docker image inspect "$ref" -f '{{.Id}}' 2>/dev/null || echo "not-pulled")
    echo "    {\"ref\": \"$ref\", \"id\": \"$id\"},"
  done | sed '$ s/,$//'
  echo "  ]"
  echo "}"
} > "$OUT/bundle.json"
echo "wrote $OUT/bundle.json"
