"""Unit tests for the hardware preflight probe."""

from __future__ import annotations

import pytest

from src.hardware import (
    DISK_MIN_BYTES,
    DISK_RECOMMENDED_BYTES,
    RAM_MIN_BYTES,
    RAM_RECOMMENDED_BYTES,
    HardwareReport,
    Reading,
    Status,
    classify,
    probe,
)


def test_classify_ok_when_at_or_above_recommended() -> None:
    assert classify(detected=16, minimum=8, recommended=16) == Status.OK
    assert classify(detected=32, minimum=8, recommended=16) == Status.OK


def test_classify_warn_when_between_minimum_and_recommended() -> None:
    assert classify(detected=8, minimum=8, recommended=16) == Status.WARN
    assert classify(detected=12, minimum=8, recommended=16) == Status.WARN


def test_classify_fail_when_below_minimum() -> None:
    assert classify(detected=4, minimum=8, recommended=16) == Status.FAIL
    assert classify(detected=0, minimum=8, recommended=16) == Status.FAIL


def test_probe_assembles_report_with_all_four_rows() -> None:
    # Arrange — DI'd readers so we don't depend on the host shape
    report = probe(
        cores_reader=lambda: 16,
        ram_bytes_reader=lambda: RAM_RECOMMENDED_BYTES,
        disk_bytes_reader=lambda: DISK_RECOMMENDED_BYTES,
        nic_mbps_reader=lambda: 10_000,
    )

    # Assert
    assert report.cores.detected == 16
    assert report.ram_bytes.detected == RAM_RECOMMENDED_BYTES
    assert report.disk_bytes.detected == DISK_RECOMMENDED_BYTES
    assert report.nic_mbps.detected == 10_000


def test_probe_overall_status_is_worst_row() -> None:
    # Arrange — RAM at min (warn), others ok
    report = probe(
        cores_reader=lambda: 16,
        ram_bytes_reader=lambda: RAM_MIN_BYTES,
        disk_bytes_reader=lambda: DISK_RECOMMENDED_BYTES,
        nic_mbps_reader=lambda: 10_000,
    )

    # Assert
    assert report.ram_bytes.status == Status.WARN
    assert report.overall_status == Status.WARN


def test_probe_overall_status_fail_dominates_warn() -> None:
    # Arrange — one fail + one warn
    report = probe(
        cores_reader=lambda: 4,  # fail
        ram_bytes_reader=lambda: RAM_MIN_BYTES,  # warn
        disk_bytes_reader=lambda: DISK_RECOMMENDED_BYTES,
        nic_mbps_reader=lambda: 10_000,
    )

    # Assert
    assert report.overall_status == Status.FAIL


def test_report_serializes_to_designer_contract_keys() -> None:
    # Arrange
    report = HardwareReport(
        cores=Reading(detected=16, minimum=8, recommended=16, status=Status.OK),
        ram_bytes=Reading(
            detected=RAM_RECOMMENDED_BYTES,
            minimum=RAM_MIN_BYTES,
            recommended=RAM_RECOMMENDED_BYTES,
            status=Status.OK,
        ),
        disk_bytes=Reading(
            detected=DISK_RECOMMENDED_BYTES,
            minimum=DISK_MIN_BYTES,
            recommended=DISK_RECOMMENDED_BYTES,
            status=Status.OK,
        ),
        nic_mbps=Reading(
            detected=10_000, minimum=1_000, recommended=10_000, status=Status.OK
        ),
        overall_status=Status.OK,
    )

    # Act
    body = report.model_dump(by_alias=True)

    # Assert — keys match the wizard JSX's HW_SCENARIOS shape (camelCase)
    assert set(body.keys()) == {
        "cores",
        "ramBytes",
        "diskBytes",
        "nicMbps",
        "overallStatus",
    }
    assert set(body["cores"].keys()) == {"detected", "min", "recommended", "status"}


@pytest.mark.parametrize(
    "status,expected",
    [
        (Status.OK, "ok"),
        (Status.WARN, "warn"),
        (Status.FAIL, "fail"),
    ],
)
def test_status_serializes_as_lowercase_string(status: Status, expected: str) -> None:
    assert status.value == expected
