# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.ecosystem_contracts import VEX_ECOSYSTEM_CONTRACT


def test_ecosystem_contract_declared():
    assert VEX_ECOSYSTEM_CONTRACT["version"].startswith("1.")
    assert "bijux_rar" in VEX_ECOSYSTEM_CONTRACT
    assert "bijux_rag" in VEX_ECOSYSTEM_CONTRACT
