#!/bin/bash
# Remaster the OFFICIAL Debian 12 ISO into the ARCNODE appliance installer:
# inject the unattended preseed + the airgap payload, make it auto-install,
# repack hybrid BIOS+UEFI with xorriso. Run at the bench (network for the base
# ISO + payload assembly).
#
# CRITICAL: the output MUST be boot-tested (qemu BIOS + UEFI, then real hardware)
# before it ships — the install medium is the historical bug surface.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"     # repo root
WORK="${WORK:-/tmp/arcnode-iso}"
BASE_ISO="${BASE_ISO:-$WORK/debian-12-dvd1.amd64.iso}"
OUT="${OUT:-$WORK/arcnode-appliance.iso}"
BASE_URL="https://cdimage.debian.org/cdimage/archive/12.11.0/amd64/iso-dvd/debian-12.11.0-amd64-DVD-1.iso"

mkdir -p "$WORK"
[ -f "$BASE_ISO" ] || { echo "fetching base Debian ISO..."; curl -fsSL "$BASE_URL" -o "$BASE_ISO"; }

echo "== extract base ISO =="
rm -rf "$WORK/iso"; osirrox -indev "$BASE_ISO" -extract / "$WORK/iso" 2>/dev/null || \
  { mkdir -p "$WORK/iso"; bsdtar -C "$WORK/iso" -xf "$BASE_ISO"; }
chmod -R u+w "$WORK/iso"

echo "== inject preseed =="
cp "$HERE/iso/preseed.cfg" "$WORK/iso/preseed.cfg"

echo "== assemble airgap payload → /arcnode on the ISO =="
# The runtime the ISO delivers: the ansible layer + provision bootstrap, plus
# the offline bundles. bundle.tar / debs / ollama models are produced by
# tools/bundle-images.sh + (task 7/8) and copied in here.
mkdir -p "$WORK/iso/arcnode"
rsync -a --exclude '.git' "$HERE/ansible" "$HERE/cfg.yml" "$HERE/install" "$WORK/iso/arcnode/"
# TODO(payload): cp "$BUNDLE/bundle.tar" "$WORK/iso/arcnode/images/"  (task 6 output)
# TODO(payload): cp -a "$DEBS" "$WORK/iso/arcnode/debs/"             (task 7 output)
# TODO(payload): cp -a "$MODELS" "$WORK/iso/arcnode/ollama-models/"  (task 8 output)

echo "== make it auto-install (BIOS isolinux + UEFI grub) =="
# BIOS: replace isolinux.cfg entirely — no graphical menu, boot our entry
# immediately (prompt 0, timeout 1) and mirror to serial for headless installs.
# Prepending to txt.cfg does NOT override Debian's vesamenu default, which just
# sits waiting for input.
cat > "$WORK/iso/isolinux/isolinux.cfg" <<'CFG'
serial 0 115200
default arcnode
prompt 0
timeout 1
label arcnode
  kernel /install.amd/vmlinuz
  append vga=788 initrd=/install.amd/initrd.gz auto=true priority=critical preseed/file=/cdrom/preseed.cfg console=tty0 console=ttyS0,115200 ---
CFG

# UEFI: prepend our entry + default + short timeout + serial, keep the rest.
if [ -f "$WORK/iso/boot/grub/grub.cfg" ]; then
  grubcfg="$WORK/iso/boot/grub/grub.cfg"
  { cat <<'GRUB'
serial --unit=0 --speed=115200
terminal_input serial console
terminal_output serial console
set default="arcnode"
set timeout=1
menuentry "arcnode" {
    linux /install.amd/vmlinuz auto=true priority=critical preseed/file=/cdrom/preseed.cfg vga=788 console=tty0 console=ttyS0,115200 ---
    initrd /install.amd/initrd.gz
}
GRUB
  } > "$grubcfg.new"
  # strip the base config's own default/timeout so ours win, append the rest
  grep -vE '^\s*(set default|set timeout|set default=|timeout)' "$grubcfg" >> "$grubcfg.new"
  mv "$grubcfg.new" "$grubcfg"
fi

echo "== repack hybrid BIOS+UEFI with xorriso =="
# Reuse the base ISO's own El Torito + EFI boot records for correctness.
xorriso -indev "$BASE_ISO" -report_el_torito as_mkisofs > "$WORK/eltorito.opts" 2>/dev/null || true
xorriso -as mkisofs -r -V 'ARCNODE_APPLIANCE' \
  -o "$OUT" \
  -J -joliet-long \
  -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
  -c isolinux/boot.cat -b isolinux/isolinux.bin \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
  -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot -isohybrid-gpt-basdat \
  "$WORK/iso"
echo "built: $OUT"
echo "NEXT (required): boot-test — qemu BIOS + UEFI, then the Hetzner box."
