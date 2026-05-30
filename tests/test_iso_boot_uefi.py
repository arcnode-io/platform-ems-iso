"""Boot the ISO under UEFI (OVMF) firmware and assert the install path works.

Catches the EFI-vs-BIOS class of bug that test_iso_boot.py misses by
booting via legacy BIOS only. Real customer hardware is overwhelmingly
UEFI today; Rob Ristroph 2026-05-30 hit "GRUB chainboots to disk" on
UEFI hardware that our BIOS-only test never reproduced.

Single test by design — booting the ISO twice (BIOS + UEFI) per pipeline
is the cost; we already get full wizard contract coverage from
test_iso_boot.py, so the UEFI variant only needs to assert that the
boot+install+wizard path completes at all.
"""

from __future__ import annotations

import httpx

from tests.iso_fixtures import booted_iso_uefi, iso_path  # pytest fixture imports


def test_uefi_boot_reaches_wizard(booted_iso_uefi: str) -> None:
    """UEFI boot → GRUB → live installer → wizard responds on port 80.

    If this fails, EFI grub.cfg's `set default=` likely didn't match
    the install menuentry (string-match weirdness with UTF-8 em-dashes,
    missing entries because EFI grub.cfg differs from BIOS, etc.), or
    the install path itself broke under UEFI.
    """
    # Act
    resp = httpx.get(f"{booted_iso_uefi}/setup/identity", timeout=10.0)

    # Assert — same minimal sanity that the BIOS test asserts; if this
    # 200s, the whole boot chain (UEFI firmware → grub → install kernel
    # → live-installer → reboot → systemd → wizard) survived.
    assert resp.status_code == 200
    assert "customer" in resp.json()
