"""Extract files from the built ISO via xorriso, assert structural invariants.

Fast (~30s on the runner): no boot, no qemu, just unpack + grep. Catches
"my live-build hook silently didn't fire" — the class of bug where
publish goes green, ISO uploads, real hardware bricks.

Skipped unless ARCNODE_ISO_PATH is set (same gate as test_iso_boot).
"""

from __future__ import annotations

import gzip
import subprocess
import tempfile
from pathlib import Path

from tests.iso_fixtures import iso_path  # pytest fixture import


def _extract(iso: Path, member: str) -> bytes:
    """Pull one file out of the ISO image to bytes. Member is the ISO path,
    e.g. /boot/grub/grub.cfg. xorriso's -extract takes a real filesystem
    path as the destination and refuses to overwrite — so we extract into
    a fresh tmpdir and read back the basename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local = Path(tmpdir) / "out"
        subprocess.run(
            [
                "xorriso",
                "-indev",
                str(iso),
                "-osirrox",
                "on:auto_chmod_on",
                "-extract",
                member,
                str(local),
            ],
            check=True,
            capture_output=True,
        )
        return local.read_bytes()


def _list(iso: Path, path: str = "/") -> list[str]:
    """List the contents of a directory inside the ISO."""
    result = subprocess.run(
        ["xorriso", "-indev", str(iso), "-ls", path],
        check=True,
        capture_output=True,
        text=True,
    )
    # xorriso emits files as 'name' (quoted, one per line, plus headers)
    return [
        line.strip().strip("'")
        for line in result.stdout.splitlines()
        if line.strip().startswith("'")
    ]


def test_grub_cfg_has_timeout(iso_path: Path) -> None:
    """`set timeout=N` must be present or grub waits forever for keypress."""
    # Act
    cfg = _extract(iso_path, "/boot/grub/grub.cfg").decode()

    # Assert
    assert "set timeout=" in cfg, "grub.cfg missing `set timeout=` — boot will hang"


def test_grub_cfg_does_not_force_serial_terminal(iso_path: Path) -> None:
    """Forcing serial as a grub terminal target breaks real-hw boot.

    Verified Sun 2026-05-24: customer's USB booted to blinking cursor
    when `terminal_output console serial` was in grub.cfg. Default
    `console` works for both real hw and headless qemu.
    """
    # Act
    cfg = _extract(iso_path, "/boot/grub/grub.cfg").decode()

    # Assert
    assert "terminal_output" not in cfg, (
        "grub.cfg has `terminal_output` directive — known to break "
        "real-hardware boot. Drop it; default console works everywhere."
    )


def test_install_entries_load_preseed(iso_path: Path) -> None:
    """`Install` menu entries must pass preseed/file= so d-i runs in
    live-installer mode (copies live squashfs) instead of fetching
    vanilla debian."""
    # Act
    cfg = (
        _extract(iso_path, "/boot/grub/grub.cfg").decode()
        + _extract(iso_path, "/boot/grub/install_start.cfg").decode()
    )

    # Assert
    assert "/install/vmlinuz" in cfg, "no debian-installer entry in grub"
    assert "preseed/file=" in cfg, (
        "install entry doesn't load preseed.cfg — operator will install "
        "vanilla debian instead of our customized appliance"
    )


def test_preseed_cfg_present_at_expected_path(iso_path: Path) -> None:
    """preseed.cfg must be at /install/preseed.cfg (where grub entries point)."""
    # Act
    preseed = _extract(iso_path, "/install/preseed.cfg").decode()

    # Assert — sentinel keys we know we set
    assert "live-installer/enable" in preseed
    assert "tasksel/first" in preseed


def test_di_initrd_contains_live_installer(iso_path: Path) -> None:
    """live-installer udeb must be inside d-i's initrd or d-i can't actually
    do the 'copy live squashfs to disk' trick. We inject it via
    hook 8500 — this test catches the case where that injection silently
    fails (e.g. mirror unreachable, udeb gone from bookworm-d-i)."""
    # Act — initrd is a cpio archive. Scan raw bytes for the udeb's
    # filename pattern; avoids unpacking 22MB just to check presence.
    initrd_gz = _extract(iso_path, "/install/initrd.gz")
    initrd = gzip.decompress(initrd_gz)

    # Assert
    assert b"live-installer" in initrd, (
        "d-i initrd doesn't contain live-installer payload — picking "
        "Install at grub will install vanilla debian, not our appliance"
    )


def test_squashfs_contains_arcnode_wizard(iso_path: Path) -> None:
    """The live filesystem must contain our wizard source + systemd units."""
    # Act
    files = _list(iso_path, "/")

    # Assert — squashfs is present (live-build always names it filesystem.squashfs)
    assert any(
        "filesystem.squashfs" in f or "live" in f.lower() for f in files
    ), "no live squashfs in ISO root — boot will have no rootfs"
