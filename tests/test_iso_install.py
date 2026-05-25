"""Drive the install path end-to-end in qemu.

1. Boot ISO with `-boot d` (CD first), select Install via grub serial input
2. Wait for d-i to complete the fully-preseeded install (~5-10 min)
3. d-i reboots qemu; on second boot we want it to come from disk, not CD
4. Once booted from disk, wizard should bind port 80 → assert 200

Slowest test we have (~15-20 min). Runs only in CI; skipped unless
ARCNODE_ISO_PATH is set.
"""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pexpect
import pytest

from tests.iso_fixtures import iso_path  # pytest fixture import

INSTALL_TIMEOUT_S = 60 * 60  # 60 min: at 35 min d-i was at "Installing the
                              # system" 60% (squashfs copy phase — the slowest).
                              # qemu single-thread + 3.4GB rsync = legitimately slow.
POST_INSTALL_BOOT_S = 6 * 60  # 6 min: systemd brings everything up


def _pick_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def installed_iso(
    iso_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    """Boot ISO, drive d-i install, reboot from disk, yield wizard URL."""
    work = tmp_path_factory.mktemp("install")
    disk = work / "disk.qcow2"
    subprocess.run(
        ["qemu-img", "create", "-f", "qcow2", str(disk), "20G"],
        check=True,
        capture_output=True,
    )

    host_port = _pick_free_port()

    # ---- Phase 1: Install ----
    # Extract d-i kernel + initrd from the ISO, boot qemu with -kernel/-initrd
    # directly. Bypasses grub entirely — way more reliable than driving the
    # grub menu via pexpect (grub doesn't write to serial in our config, so
    # pexpect can't time the 'i' keypress against the menu).
    vmlinuz = work / "install-vmlinuz"
    initrd = work / "install-initrd.gz"
    for member, dst in [("/install/vmlinuz", vmlinuz), ("/install/initrd.gz", initrd)]:
        subprocess.run(
            [
                "xorriso",
                "-indev",
                str(iso_path),
                "-osirrox",
                "on:auto_chmod_on",
                "-extract",
                member,
                str(dst),
            ],
            check=True,
            capture_output=True,
        )

    serial_log = work / "install-serial.log"
    # Pass the preseed args directly via -append; same as what our grub
    # entries already set after hook 9999 patches them.
    install_cmd = (
        "qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m 4096 "
        f"-drive file={disk},format=qcow2,if=virtio "
        f"-cdrom {iso_path} "
        f"-kernel {vmlinuz} -initrd {initrd} "
        "-append 'auto=true priority=critical "
        "preseed/file=/cdrom/install/preseed.cfg "
        "console=ttyS0,115200n8' "
        "-display none -monitor none "
        f"-serial mon:stdio"
    )
    p = pexpect.spawn(install_cmd, encoding="utf-8", timeout=120)
    p.logfile_read = serial_log.open("w")  # closed implicitly when p is killed

    # Wait for "Installation complete" — d-i prints this right before reboot
    print("\n=== install started, waiting up to 20 min ===", flush=True)
    deadline = time.monotonic() + INSTALL_TIMEOUT_S
    install_done = False
    while time.monotonic() < deadline:
        try:
            p.expect(
                ["Installation complete", "Installation step failed", "Power down"],
                timeout=30,
            )
            install_done = True
            break
        except pexpect.TIMEOUT:
            continue
    if not install_done:
        p.terminate()
        # Dump the tail of the pexpect logfile so we can see WHERE d-i
        # stalled. Without this, "install didn't complete in 1200s" is
        # useless — could be grub never got picked, could be a missing
        # preseed answer hanging at a prompt, could be live-installer
        # rsync just being slow.
        log_tail = ""
        if serial_log.exists():
            log_tail = serial_log.read_text(errors="replace")[-4000:]
        pytest.fail(
            f"install didn't complete in {INSTALL_TIMEOUT_S}s\n"
            f"--- serial.log tail (last 4KB) ---\n{log_tail}"
        )

    # d-i reboots; let qemu exit cleanly. We'll restart it with -boot c.
    print("\n=== install complete, killing qemu to switch boot order ===", flush=True)
    p.terminate(force=True)

    # ---- Phase 2: Boot from disk ----
    boot_cmd = [
        "qemu-system-x86_64",
        "-enable-kvm",
        "-cpu",
        "host",
        "-smp",
        "2",
        "-m",
        "4096",
        "-drive",
        f"file={disk},format=qcow2,if=virtio",
        "-boot",
        "c",
        "-netdev",
        f"user,id=net0,hostfwd=tcp:127.0.0.1:{host_port}-:80",
        "-device",
        "virtio-net-pci,netdev=net0",
        "-display",
        "none",
        "-vga",
        "std",
        "-serial",
        f"file:{work / 'post-install-serial.log'}",
        "-monitor",
        "none",
    ]
    qemu = subprocess.Popen(
        boot_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{host_port}"
    print(f"\n=== booting from disk, polling {base_url} ===", flush=True)
    deadline = time.monotonic() + POST_INSTALL_BOOT_S
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base_url}/setup/identity", timeout=3.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        if qemu.poll() is not None:
            tail = (work / "post-install-serial.log").read_text()[-2000:]
            pytest.fail(
                f"qemu died post-install ({qemu.returncode}). serial tail:\n{tail}"
            )
        time.sleep(5)
    else:
        qemu.kill()
        tail = (work / "post-install-serial.log").read_text()[-2000:]
        pytest.fail(f"wizard never bound :80 after install. serial tail:\n{tail}")

    print("\n=== installed system live + wizard responding ===", flush=True)
    try:
        yield base_url
    finally:
        qemu.kill()
        qemu.wait(timeout=10)


def test_installed_system_serves_wizard_identity(installed_iso: str) -> None:
    """After d-i install + reboot from disk, wizard answers identity."""
    # Act
    resp = httpx.get(f"{installed_iso}/setup/identity", timeout=10.0)

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    for key in ("customer", "site", "market", "isoVersion"):
        assert key in body, f"identity payload missing {key}: {body}"


def test_installed_system_renders_wizard_html(installed_iso: str) -> None:
    """GET / on the installed system renders the Jinja template."""
    # Act
    resp = httpx.get(f"{installed_iso}/", timeout=10.0)

    # Assert
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "window.INSTALL_IDENTITY" in resp.text
