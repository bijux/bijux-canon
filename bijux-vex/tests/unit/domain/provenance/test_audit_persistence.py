# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import json
from pathlib import Path

from bijux_vex.contracts.tx import Tx
from bijux_vex.domain.provenance.audit import AuditRecord, chain_hash
from bijux_vex.infra.adapters.memory.backend import memory_backend


def _serialize(log: list[AuditRecord], path: Path) -> None:
    payload = [
        {
            "record_id": r.record_id,
            "tx_id": r.tx_id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "actor": r.actor,
            "prev_hash": r.prev_hash,
            "details": list(r.details),
            "record_hash": r.record_hash,
        }
        for r in log
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def _deserialize(path: Path) -> list[AuditRecord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        AuditRecord(
            record_id=entry["record_id"],
            tx_id=entry["tx_id"],
            action=entry["action"],
            resource_type=entry["resource_type"],
            resource_id=entry["resource_id"],
            actor=entry["actor"],
            prev_hash=entry["prev_hash"],
            details=tuple(tuple(pair) for pair in entry["details"]),
            record_hash=entry["record_hash"],
        )
        for entry in raw
    ]


def test_audit_chain_persists_and_validates(tmp_path: Path):
    backend = memory_backend()
    with backend.tx_factory() as tx:
        _touch(tx)
    with backend.tx_factory() as tx:
        _touch(tx)

    audit_log = backend.stores.vectors._state.audit_log  # type: ignore[attr-defined]
    dump_path = tmp_path / "audit.json"
    _serialize(audit_log, dump_path)

    restored = _deserialize(dump_path)
    for idx, record in enumerate(restored):
        expected_prev = restored[idx - 1].record_hash if idx > 0 else None
        assert record.prev_hash == expected_prev
        assert record.record_hash == chain_hash(record)


def _touch(tx: Tx) -> None:
    # no-op write to create audit record
    pass
