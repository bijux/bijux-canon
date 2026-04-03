# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Audit record schema with hash chaining.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bijux_vex.core.identity.ids import fingerprint


@dataclass(frozen=True)
class AuditRecord:
    record_id: str
    tx_id: str
    action: str
    resource_type: str
    resource_id: str
    actor: str | None
    prev_hash: str | None
    details: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    record_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", tuple(tuple(p) for p in self.details))
        if self.record_hash is None:
            object.__setattr__(self, "record_hash", chain_hash(self))


def chain_hash(record: AuditRecord) -> str:
    """
    Compute a hash that chains to the previous record.
    prev_hash participates in the fingerprint; a missing prev_hash starts a new chain.
    """
    payload = {
        "record_id": record.record_id,
        "tx_id": record.tx_id,
        "action": record.action,
        "resource_type": record.resource_type,
        "resource_id": record.resource_id,
        "actor": record.actor,
        "prev_hash": record.prev_hash,
        "details": list(record.details),
    }
    return fingerprint(payload, canon_version="v1")
