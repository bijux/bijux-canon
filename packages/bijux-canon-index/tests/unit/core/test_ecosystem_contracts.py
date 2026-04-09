# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.ecosystem_contracts import VEX_ECOSYSTEM_CONTRACT


def test_ecosystem_contract_declared():
    assert VEX_ECOSYSTEM_CONTRACT["version"].startswith("1.")
    assert "bijux_rar" in VEX_ECOSYSTEM_CONTRACT
    assert "bijux_rag" in VEX_ECOSYSTEM_CONTRACT
