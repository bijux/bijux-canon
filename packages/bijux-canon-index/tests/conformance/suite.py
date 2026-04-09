# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, NamedTuple, cast

from bijux_canon_index.contracts.authz import Authz
from bijux_canon_index.contracts.resources import ExecutionResources
from bijux_canon_index.contracts.tx import Tx


class ConformanceFixture(NamedTuple):
    tx_factory: Callable[[], Tx]
    stores: ExecutionResources
    authz: Authz
    name: str


class BackendCase(NamedTuple):
    name: str
    factory: Callable[[], ConformanceFixture]


def parametrize_backends(backends: Iterable[BackendCase]) -> Any:
    import pytest

    ids = [case.name for case in backends]
    return pytest.mark.parametrize("backend_case", backends, ids=ids)


def default_backends() -> Iterable[BackendCase]:
    from bijux_canon_index.infra.adapters.memory.backend import memory_backend
    from bijux_canon_index.infra.adapters.sqlite.backend import sqlite_backend

    def _sqlite_default() -> ConformanceFixture:
        return cast(ConformanceFixture, sqlite_backend(str(Path(":memory:"))))

    return [
        BackendCase(
            name="memory",
            factory=cast(Callable[[], ConformanceFixture], memory_backend),
        ),
        BackendCase(name="sqlite", factory=_sqlite_default),
    ]
