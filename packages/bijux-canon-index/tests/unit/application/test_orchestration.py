# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any, cast

from bijux_canon_index.contracts.authz import Authz


class SpyAuthz:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def check(
        self,
        tx: object,
        *,
        action: str,
        resource: str,
        actor: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        del tx, actor, context
        self.calls.append((action, resource))
        return


def test_ingest_uses_authz_and_tx(monkeypatch: Any) -> None:
    from bijux_canon_index.application.engine import VectorExecutionEngine
    from bijux_canon_index.infra.adapters.memory.backend import memory_backend
    from bijux_canon_index.interfaces.schemas.models import IngestRequest

    backend = memory_backend()
    spy = SpyAuthz()
    orch = VectorExecutionEngine(backend=backend, authz=cast(Authz, spy))

    orch.ingest(IngestRequest(documents=["hi"], vectors=[[0.0]]))
    assert ("put_document", "document") in spy.calls
    # audit log should have one record from commit
    backend_state = getattr(backend.stores.vectors, "_state", None)
    assert backend_state is not None
    assert backend_state.audit_log
