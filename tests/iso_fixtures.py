"""Fixtures for boot-the-built-ISO integration tests.

Per the project rule (no conftest.py), fixtures live in a normal module
and are imported explicitly by every test file that needs them.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest


def _pick_free_port() -> int:
    """OS-assigned ephemeral port — avoids host-port clashes when the runner
    runs multiple jobs in parallel."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def iso_path() -> Path:
    """Path to the built ISO. CI sets ARCNODE_ISO_PATH after `lb build`;
    locally you can `export ARCNODE_ISO_PATH=live-build/arcnode-ems-1.0.0.iso`.
    Skips the suite if unset — these tests aren't unit tests, they need a
    real artifact + qemu-kvm + KVM."""
    raw = os.environ.get("ARCNODE_ISO_PATH")
    if not raw:
        pytest.skip("ARCNODE_ISO_PATH unset — boot tests require a built ISO")
    p = Path(raw)
    if not p.exists():
        pytest.fail(f"ARCNODE_ISO_PATH={p} does not exist")
    return p


@pytest.fixture(scope="session")
def booted_iso(
    iso_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    """Boot the ISO headless in qemu-kvm, yield the wizard's base URL.

    Tears down on session exit. ~3-7 minute boot on first run; tests should
    poll the wizard with a generous timeout, not assume it's instantly up.
    """
    work = tmp_path_factory.mktemp("qemu")
    disk = work / "disk.qcow2"
    subprocess.run(
        ["qemu-img", "create", "-f", "qcow2", str(disk), "20G"],
        check=True,
        capture_output=True,
    )

    host_port = _pick_free_port()
    # Reason: `-nographic` redirects VGA to serial which trips grub's
    # terminal rendering (interleaves error strings with cursor-positioning
    # escape codes; the boot menu never auto-advances). `-display none`
    # keeps a virtual VGA framebuffer (which grub renders to and qemu
    # drops on the floor), `-serial file:` keeps kernel logs for debug.
    qemu = subprocess.Popen(
        [
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
            "-cdrom",
            str(iso_path),
            "-boot",
            "d",
            "-netdev",
            f"user,id=net0,hostfwd=tcp:127.0.0.1:{host_port}-:80",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-display",
            "none",
            "-vga",
            "std",
            "-serial",
            f"file:{work / 'serial.log'}",
            "-monitor",
            "none",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{host_port}"
    deadline = time.monotonic() + 420  # 7 minutes — first live boot is slow
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base_url}/setup/identity", timeout=3.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        if qemu.poll() is not None:
            pytest.fail(
                f"qemu exited early ({qemu.returncode}); "
                f"serial.log tail:\n{(work / 'serial.log').read_text()[-2000:]}"
            )
        time.sleep(5)
    else:
        qemu.kill()
        pytest.fail(
            f"wizard never answered within 420s; "
            f"serial.log tail:\n{(work / 'serial.log').read_text()[-2000:]}"
        )

    try:
        yield base_url
    finally:
        qemu.kill()
        qemu.wait(timeout=10)


# OVMF/edk2 firmware paths vary by distro. Try the common ones; skip the
# UEFI fixture if none found (test_iso_boot_uefi.py reports skip cleanly).
_OVMF_CODE_CANDIDATES = (
    "/usr/share/edk2/x64/OVMF_CODE.4m.fd",  # Arch
    "/usr/share/OVMF/OVMF_CODE.fd",  # Debian/Ubuntu
    "/usr/share/edk2-ovmf/x64/OVMF_CODE.fd",  # Fedora
)
_OVMF_VARS_CANDIDATES = (
    "/usr/share/edk2/x64/OVMF_VARS.4m.fd",
    "/usr/share/OVMF/OVMF_VARS.fd",
    "/usr/share/edk2-ovmf/x64/OVMF_VARS.fd",
)


def _find_ovmf() -> tuple[Path, Path] | None:
    """Return (CODE, VARS) firmware paths, or None if OVMF isn't installed."""
    code = next((Path(p) for p in _OVMF_CODE_CANDIDATES if Path(p).exists()), None)
    vars_ = next((Path(p) for p in _OVMF_VARS_CANDIDATES if Path(p).exists()), None)
    if code and vars_:
        return code, vars_
    return None


@pytest.fixture(scope="session")
def booted_iso_uefi(
    iso_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    """Same as ``booted_iso`` but boots the ISO under UEFI (OVMF) firmware.

    Catches the EFI-vs-BIOS class of bug — e.g. EFI grub.cfg lacking
    menuentries that the BIOS path has, or `set default=` not matching
    under EFI's grub. Real customer hardware (Rob Ristroph 2026-05-30)
    is UEFI; our existing booted_iso fixture only exercises BIOS.
    Skips when OVMF isn't installed on the runner (install via
    `pacman -S edk2-ovmf` on arch, `apt install ovmf` on debian).
    """
    firmware = _find_ovmf()
    if firmware is None:
        pytest.skip("OVMF/edk2 firmware not found — install ovmf/edk2-ovmf")
    code, vars_src = firmware

    work = tmp_path_factory.mktemp("qemu-uefi")
    disk = work / "disk.qcow2"
    subprocess.run(
        ["qemu-img", "create", "-f", "qcow2", str(disk), "20G"],
        check=True,
        capture_output=True,
    )
    # OVMF VARS file holds per-VM NVRAM — copy the template so we don't
    # mutate the system-wide one.
    vars_local = work / "OVMF_VARS.fd"
    vars_local.write_bytes(vars_src.read_bytes())

    host_port = _pick_free_port()
    qemu = subprocess.Popen(
        [
            "qemu-system-x86_64",
            "-enable-kvm",
            "-cpu",
            "host",
            "-smp",
            "2",
            "-m",
            "4096",
            # UEFI firmware as two pflash drives (CODE + VARS).
            "-drive",
            f"if=pflash,format=raw,readonly=on,file={code}",
            "-drive",
            f"if=pflash,format=raw,file={vars_local}",
            "-drive",
            f"file={disk},format=qcow2,if=virtio",
            "-cdrom",
            str(iso_path),
            "-boot",
            "d",
            "-netdev",
            f"user,id=net0,hostfwd=tcp:127.0.0.1:{host_port}-:80",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-display",
            "none",
            "-vga",
            "std",
            "-serial",
            f"file:{work / 'serial.log'}",
            "-monitor",
            "none",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base_url = f"http://127.0.0.1:{host_port}"
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{base_url}/setup/identity", timeout=3.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        if qemu.poll() is not None:
            pytest.fail(
                f"qemu (UEFI) exited early ({qemu.returncode}); "
                f"serial.log tail:\n{(work / 'serial.log').read_text()[-2000:]}"
            )
        time.sleep(5)
    else:
        qemu.kill()
        pytest.fail(
            f"wizard never answered within 420s (UEFI boot); "
            f"serial.log tail:\n{(work / 'serial.log').read_text()[-2000:]}"
        )

    try:
        yield base_url
    finally:
        qemu.kill()
        qemu.wait(timeout=10)
