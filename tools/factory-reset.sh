#!/bin/bash
# DESTRUCTIVE: wipe all appliance state — telemetry, DB volumes, generated
# credentials. The OS + ansible layer stay intact; the next boot re-converges
# from scratch with brand-new secrets.
set -euo pipefail
if [ "${1:-}" != "--yes" ]; then
  echo "This ERASES all telemetry, DB volumes, and generated credentials."
  read -r -p "Type 'factory-reset' to confirm: " ans
  [ "$ans" = "factory-reset" ] || { echo "aborted"; exit 1; }
fi
docker compose -f /opt/arcnode/stack/compose.yml down -v || true
rm -rf /opt/arcnode/secrets /opt/arcnode/stack/.env /opt/arcnode/stack/credentials.xml
echo "wiped. reboot (or: systemctl start arcnode.service) to re-converge fresh."
