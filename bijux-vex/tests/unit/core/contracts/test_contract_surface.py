# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from bijux_vex.core.contracts.execution_contract import ExecutionContract


def test_contract_surface_matrix_and_levels():
    matrix = ExecutionContract.surface_matrix()
    assert matrix["deterministic"] == "SUPPORTED"
    assert matrix["non_deterministic"] == "STABLE_BOUNDED"
    assert ExecutionContract.DETERMINISTIC.support_level == "SUPPORTED"
    assert ExecutionContract.NON_DETERMINISTIC.support_level == "STABLE_BOUNDED"
