# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.infra.adapters.memory.backend import memory_backend


def test_audit_compaction_retains_tail():
    backend = memory_backend()
    state = backend.stores.vectors._state  # type: ignore[attr-defined]
    # simulate audit records
    from bijux_vex.domain.provenance.audit import AuditRecord

    for i in range(5):
        state.append_audit(
            AuditRecord(
                record_id=str(i),
                tx_id=str(i),
                action="commit",
                resource_type="doc",
                resource_id=str(i),
                actor=None,
                prev_hash=None,
                details=(),
            )
        )
    state.compact_audit(retention=2)
    assert len(state.audit_log) == 2
    assert state.audit_log[0].record_id == "3"
