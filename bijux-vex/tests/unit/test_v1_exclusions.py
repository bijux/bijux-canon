# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.v1_exclusions import V1_EXCLUSIONS, ensure_excluded


def test_all_exclusions_raise():
    for name in V1_EXCLUSIONS:
        with pytest.raises(NotImplementedError):
            ensure_excluded(name)


def test_unknown_feature_rejected():
    with pytest.raises(KeyError):
        ensure_excluded("unknown-feature")
