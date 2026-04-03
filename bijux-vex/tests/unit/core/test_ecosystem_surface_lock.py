# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import importlib
import pytest


ALLOWED_ECOSYSTEM_MODULES = {
    "bijux_vex.core.types",
    "bijux_vex.core.contracts.execution_contract",
    "bijux_vex.core.execution_result",
    "bijux_vex.core.runtime.execution_plan",
    "bijux_vex.core.runtime.vector_execution",
    "bijux_vex.core.runtime.execution_session",
    "bijux_vex.domain.execution_requests.execute",
    "bijux_vex.domain.execution_requests.compare",
}


def test_internal_modules_not_exposed_to_ecosystem():
    forbidden = [
        "bijux_vex.domain.execution_algorithms",
        "bijux_vex.infra.adapters.memory.backend",
        "bijux_vex.infra.adapters.sqlite.backend",
    ]
    for mod in forbidden:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(mod + "_forbidden")

    for mod in ALLOWED_ECOSYSTEM_MODULES:
        importlib.import_module(mod)
