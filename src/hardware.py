"""Hardware preflight probe — cores, RAM, disk, NIC link speed.

Matches the wire contract the designer's `hardware-check.jsx` consumes.
Reader functions are injected so unit tests don't depend on host shape;
the default readers do the real OS-level inspection.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# --- Thresholds (binary multiples; designer treats these as GB/TB) ---
GB = 1024**3
TB = 1024**4

CORES_MIN = 8
CORES_RECOMMENDED = 16
RAM_MIN_BYTES = 32 * GB
RAM_RECOMMENDED_BYTES = 64 * GB
DISK_MIN_BYTES = 256 * GB
DISK_RECOMMENDED_BYTES = 1 * TB
NIC_MIN_MBPS = 1_000  # 1 Gbps
NIC_RECOMMENDED_MBPS = 10_000  # 10 Gbps


class Status(StrEnum):
    """Three-bucket preflight verdict matching the designer's wire contract."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


def classify(*, detected: int, minimum: int, recommended: int) -> Status:
    """Three-bucket status: ok if >= recommended, fail if < minimum, warn otherwise."""
    if detected < minimum:
        return Status.FAIL
    if detected < recommended:
        return Status.WARN
    return Status.OK


def _camel(s: str) -> str:
    head, *tail = s.split("_")
    return head + "".join(t.capitalize() for t in tail)


class _Wire(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


class Reading(_Wire):
    """One row of the preflight (cores, ram, disk, or nic)."""

    detected: int
    minimum: int
    recommended: int
    status: Status

    # Reason: designer's wire contract uses `min`, not `minimum`.
    model_config = ConfigDict(
        alias_generator=lambda s: "min" if s == "minimum" else _camel(s),
        populate_by_name=True,
    )


class HardwareReport(_Wire):
    """Full preflight payload — four readings + their worst-of overall."""

    cores: Reading
    ram_bytes: Reading
    disk_bytes: Reading
    nic_mbps: Reading
    overall_status: Status


# --- Default readers ------------------------------------------------


def _default_cores_reader() -> int:
    # sched_getaffinity respects cgroups; cpu_count() doesn't.
    return len(os.sched_getaffinity(0))


def _default_ram_bytes_reader() -> int:
    # /proc/meminfo MemTotal is in kB; multiply.
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) * 1024
    return 0


def _default_disk_bytes_reader() -> int:
    return shutil.disk_usage("/").total


_SPEED_RX = re.compile(r"Speed:\s*(\d+)Mb/s")


def _default_nic_mbps_reader() -> int:
    """Link speed of the default-route interface, in Mbps. 0 if undetectable."""
    try:
        # Find default-route iface
        route = subprocess.run(
            ["ip", "-o", "route", "show", "default"],
            check=True,
            capture_output=True,
            text=True,
        )
        # "default via 10.0.0.1 dev eth0 proto dhcp ..." — iface is 5th token
        parts = route.stdout.split()
        if len(parts) < 5 or parts[3] != "dev":
            return 0
        iface = parts[4]
        # ethtool reports "Speed: 1000Mb/s" or "Speed: Unknown!"
        eth = subprocess.run(  # noqa: S603 — iface from `ip route`, trusted
            ["ethtool", iface],
            check=False,
            capture_output=True,
            text=True,
        )
        m = _SPEED_RX.search(eth.stdout)
        return int(m.group(1)) if m else 0
    except (subprocess.SubprocessError, OSError):
        return 0


# --- Composition ---------------------------------------------------


def probe(
    *,
    cores_reader: Callable[[], int] = _default_cores_reader,
    ram_bytes_reader: Callable[[], int] = _default_ram_bytes_reader,
    disk_bytes_reader: Callable[[], int] = _default_disk_bytes_reader,
    nic_mbps_reader: Callable[[], int] = _default_nic_mbps_reader,
) -> HardwareReport:
    """Run the four readers, classify each, return the assembled report."""
    cores_v = cores_reader()
    ram_v = ram_bytes_reader()
    disk_v = disk_bytes_reader()
    nic_v = nic_mbps_reader()

    readings = HardwareReport(
        cores=Reading(
            detected=cores_v,
            minimum=CORES_MIN,
            recommended=CORES_RECOMMENDED,
            status=classify(
                detected=cores_v, minimum=CORES_MIN, recommended=CORES_RECOMMENDED
            ),
        ),
        ram_bytes=Reading(
            detected=ram_v,
            minimum=RAM_MIN_BYTES,
            recommended=RAM_RECOMMENDED_BYTES,
            status=classify(
                detected=ram_v, minimum=RAM_MIN_BYTES, recommended=RAM_RECOMMENDED_BYTES
            ),
        ),
        disk_bytes=Reading(
            detected=disk_v,
            minimum=DISK_MIN_BYTES,
            recommended=DISK_RECOMMENDED_BYTES,
            status=classify(
                detected=disk_v,
                minimum=DISK_MIN_BYTES,
                recommended=DISK_RECOMMENDED_BYTES,
            ),
        ),
        nic_mbps=Reading(
            detected=nic_v,
            minimum=NIC_MIN_MBPS,
            recommended=NIC_RECOMMENDED_MBPS,
            status=classify(
                detected=nic_v, minimum=NIC_MIN_MBPS, recommended=NIC_RECOMMENDED_MBPS
            ),
        ),
        overall_status=Status.OK,  # placeholder; overwritten below
    )
    # Worst-of: fail > warn > ok
    statuses = [
        readings.cores.status,
        readings.ram_bytes.status,
        readings.disk_bytes.status,
        readings.nic_mbps.status,
    ]
    if Status.FAIL in statuses:
        readings.overall_status = Status.FAIL
    elif Status.WARN in statuses:
        readings.overall_status = Status.WARN
    else:
        readings.overall_status = Status.OK
    return readings
