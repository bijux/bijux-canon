# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations


class SpyAuthz:
    def __init__(self):
        self.calls = []

    def check(self, tx, *, action, resource, actor=None, context=None):
        self.calls.append((action, resource))
        return None


def test_ingest_uses_authz_and_tx(monkeypatch):
    from bijux_vex.services.execution_engine import VectorExecutionEngine
    from bijux_vex.infra.adapters.memory.backend import memory_backend
    from bijux_vex.boundaries.pydantic_edges.models import IngestRequest

    backend = memory_backend()
    spy = SpyAuthz()
    orch = VectorExecutionEngine(backend=backend, authz=spy)

    orch.ingest(IngestRequest(documents=["hi"], vectors=[[0.0]]))
    assert ("put_document", "document") in spy.calls
    # audit log should have one record from commit
    assert backend.stores.vectors._state.audit_log  # type: ignore[attr-defined]
