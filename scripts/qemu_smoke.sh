#!/usr/bin/env bash
# qemu_smoke.sh — boot the built ISO headless, wait for the wizard, smoke
# the identity endpoint, kill the VM.
#
# Designed to run on the iso-builder runner (qemu-kvm + libvirt already
# present) right after `lb build`. Fails the CI job if the wizard never
# answers — catches packaging regressions before the customer downloads.
#
# Usage:
#   scripts/qemu_smoke.sh <path-to.iso>
#
# Env knobs (mostly for local debugging):
#   SMOKE_TIMEOUT_S  total seconds to wait for the wizard (default 300)
#   SMOKE_HOST_PORT  host-side TCP port to forward to guest 80 (default 18080)
#   SMOKE_MEM_MB     VM memory in MB (default 4096)
#   SMOKE_DISK_GB    blank disk attached for the installer (default 20)
set -euo pipefail

ISO_PATH="${1:?usage: qemu_smoke.sh <path-to.iso>}"
test -f "$ISO_PATH" || { echo "ERROR: $ISO_PATH does not exist"; exit 1; }

TIMEOUT_S="${SMOKE_TIMEOUT_S:-300}"
HOST_PORT="${SMOKE_HOST_PORT:-18080}"
MEM_MB="${SMOKE_MEM_MB:-4096}"
DISK_GB="${SMOKE_DISK_GB:-20}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"; [ -n "${QEMU_PID:-}" ] && kill -9 "$QEMU_PID" 2>/dev/null || true' EXIT

DISK="$WORK/disk.qcow2"
qemu-img create -f qcow2 "$DISK" "${DISK_GB}G" >/dev/null
echo "==> blank disk: $DISK ($DISK_GB GB)"

echo "==> boot ISO in qemu-kvm (headless, $MEM_MB MB)"
# Reason: -nographic + -serial mon:stdio means we can monitor in background
# AND tail boot output via the redirect file. -netdev user,hostfwd plumbs
# guest:80 to host:HOST_PORT so we can curl the wizard from this script.
qemu-system-x86_64 \
  -enable-kvm \
  -cpu host -smp 2 -m "$MEM_MB" \
  -drive file="$DISK",format=qcow2,if=virtio \
  -cdrom "$ISO_PATH" \
  -boot d \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:"$HOST_PORT"-:80 \
  -device virtio-net-pci,netdev=net0 \
  -nographic \
  -serial file:"$WORK/serial.log" \
  -monitor none \
  >"$WORK/qemu.log" 2>&1 &
QEMU_PID=$!
echo "==> qemu pid=$QEMU_PID, waiting up to ${TIMEOUT_S}s for wizard on :$HOST_PORT"

# Poll the wizard's identity endpoint. First boot lands on the debian
# installer prompt — for a live-only smoke we expect arcnode-wizard to be
# active inside the live env, so :80 should answer within 2-3 min.
DEADLINE=$((SECONDS + TIMEOUT_S))
while [ $SECONDS -lt $DEADLINE ]; do
  if curl -fsS --max-time 3 "http://127.0.0.1:${HOST_PORT}/setup/identity" >"$WORK/identity.json" 2>/dev/null; then
    echo "==> wizard answered after $SECONDS s"
    echo "==> identity.json contents:"
    cat "$WORK/identity.json"
    echo
    # Smoke assertion: the JSON has at least the keys the JSX reads.
    for key in customer site market isoVersion; do
      if ! grep -q "\"$key\"" "$WORK/identity.json"; then
        echo "ERROR: identity.json missing required key '$key'"
        echo "--- last 50 lines of serial log ---"
        tail -50 "$WORK/serial.log" || true
        exit 1
      fi
    done
    echo "==> SMOKE OK"
    exit 0
  fi
  sleep 5
done

echo "ERROR: wizard never answered within ${TIMEOUT_S}s"
echo "--- last 100 lines of serial log ---"
tail -100 "$WORK/serial.log" || true
echo "--- last 50 lines of qemu stderr ---"
tail -50 "$WORK/qemu.log" || true
exit 1
