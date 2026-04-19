# SPDX-License-Identifier: Apache-2.0
"""Backend helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from bijux_canon_index.contracts.authz import AllowAllAuthz, Authz
from bijux_canon_index.contracts.resources import (
    BackendCapabilities,
    ExecutionResources,
)
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_canon_index.infra.adapters.sqlite.backend import (
    SQLiteTx,
    sqlite_backend,
)
from bijux_canon_index.infra.environment import read_env


class HnswFixture(NamedTuple):
    """Represents HNSW fixture."""

    tx_factory: Callable[[], SQLiteTx]
    stores: ExecutionResources
    authz: Authz
    name: str
    ann: AnnExecutionRequestRunner
    diagnostics: dict[str, Callable[[], object]] | None = None


def hnsw_backend(
    db_path: str = ":memory:",
    index_dir: str | Path | None = None,
) -> HnswFixture:
    """Production-grade local backend: SQLite storage + persistent HNSW ANN index."""
    base = sqlite_backend(db_path=db_path)
    try:
        from bijux_canon_index.infra.adapters.ann_hnsw import HnswAnnRunner

        runner: AnnExecutionRequestRunner = HnswAnnRunner(
            base.stores.vectors, index_dir=index_dir
        )
    except Exception:
        from bijux_canon_index.infra.adapters.ann_reference import ReferenceAnnRunner

        runner = ReferenceAnnRunner(base.stores.vectors)
    caps = BackendCapabilities(
        contracts={
            ExecutionContract.DETERMINISTIC,
            ExecutionContract.NON_DETERMINISTIC,
        },
        max_vector_size=4096,
        metrics={"l2"},
        deterministic_query=True,
        replayable=True,
        isolation_level="process",
        ann_support=True,
        supports_ann=True,
    )
    stores = ExecutionResources(
        name="hnsw",
        vectors=base.stores.vectors,
        ledger=base.stores.ledger,
        capabilities=caps,
    )
    diagnostics = dict(base.diagnostics or {})
    diagnostics["index_dir"] = lambda: str(
        Path(
            index_dir
            or read_env(
                "BIJUX_CANON_INDEX_HNSW_PATH",
                legacy="BIJUX_VEX_HNSW_PATH",
                default="artifacts/03-bijux-canon-index/hnsw_index",
            )
        ).resolve()
    )
    return HnswFixture(
        tx_factory=base.tx_factory,
        stores=stores,
        authz=AllowAllAuthz(),
        name="hnsw",
        ann=runner,
        diagnostics=diagnostics,
    )


__all__ = ["hnsw_backend", "HnswFixture"]
