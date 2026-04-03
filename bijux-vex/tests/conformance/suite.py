# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
from __future__ import annotations
from typing import Callable, Iterable, NamedTuple

from bijux_vex.contracts.authz import Authz
from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.contracts.tx import Tx


class ConformanceFixture(NamedTuple):
    tx_factory: Callable[[], Tx]
    stores: ExecutionResources
    authz: Authz
    name: str


class BackendCase(NamedTuple):
    name: str
    factory: Callable[[], ConformanceFixture]


def parametrize_backends(backends: Iterable[BackendCase]):
    import pytest

    ids = [case.name for case in backends]
    return pytest.mark.parametrize("backend_case", backends, ids=ids)


def default_backends() -> Iterable[BackendCase]:
    from bijux_vex.infra.adapters.memory.backend import memory_backend
    from bijux_vex.infra.adapters.sqlite.backend import sqlite_backend

    return [
        BackendCase(name="memory", factory=memory_backend),
        BackendCase(name="sqlite", factory=sqlite_backend),
    ]
