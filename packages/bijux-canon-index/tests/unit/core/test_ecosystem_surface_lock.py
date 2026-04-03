# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
import importlib
import pytest


ALLOWED_ECOSYSTEM_MODULES = {
    "bijux_canon_index.core.types",
    "bijux_canon_index.core.contracts.execution_contract",
    "bijux_canon_index.core.execution_result",
    "bijux_canon_index.core.runtime.execution_plan",
    "bijux_canon_index.core.runtime.vector_execution",
    "bijux_canon_index.core.runtime.execution_session",
    "bijux_canon_index.domain.execution_requests.execute",
    "bijux_canon_index.domain.execution_requests.compare",
}


def test_internal_modules_not_exposed_to_ecosystem():
    forbidden = [
        "bijux_canon_index.domain.algorithms",
        "bijux_canon_index.infra.adapters.memory.backend",
        "bijux_canon_index.infra.adapters.sqlite.backend",
    ]
    for mod in forbidden:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(mod + "_forbidden")

    for mod in ALLOWED_ECOSYSTEM_MODULES:
        importlib.import_module(mod)
