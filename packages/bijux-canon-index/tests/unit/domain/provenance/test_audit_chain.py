# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from dataclasses import replace

import pytest

from bijux_vex.domain.provenance.audit import AuditRecord, chain_hash


def _record(record_id: str, prev: str | None) -> AuditRecord:
    return AuditRecord(
        record_id=record_id,
        tx_id=record_id,
        action="commit",
        resource_type="tx",
        resource_id=record_id,
        actor="tester",
        prev_hash=prev,
        details=(("0", "action"),),
    )


def _check_chain(records: list[AuditRecord]) -> bool:
    for idx, rec in enumerate(records):
        expected_prev = records[idx - 1].record_hash if idx > 0 else None
        if rec.prev_hash != expected_prev:
            return False
        if chain_hash(rec) != rec.record_hash:
            return False
    return True


def test_chain_integrity_passes():
    first = _record("r1", None)
    second = _record("r2", first.record_hash)
    third = _record("r3", second.record_hash)
    assert _check_chain([first, second, third])


def test_chain_tamper_detected():
    first = _record("r1", None)
    second = _record("r2", first.record_hash)
    tampered = replace(second, action="tampered")
    assert not _check_chain([first, tampered])


def test_missing_prev_hash_detected():
    first = _record("r1", None)
    second = _record("r2", None)
    assert not _check_chain([first, second])
