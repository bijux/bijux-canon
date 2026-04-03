# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.version import (
    DEPRECATION_POLICY,
    PUBLIC_API_VERSION,
    assert_supported_version,
)


def test_version_policy():
    assert PUBLIC_API_VERSION.startswith("1.")
    assert "backward-compatible" in DEPRECATION_POLICY
    assert_supported_version("1.2.3")
    with pytest.raises(ValueError):
        assert_supported_version("2.0.0")
