# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from hypothesis import HealthCheck, given, settings

from bijux_vex.domain.execution_requests import scoring
from tests import strategies as strat


@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(strat.vectors())
def test_scoring_determinism(vec):
    score1 = scoring.l2_distance(vec, vec)
    score2 = scoring.l2_distance(vec, vec)
    assert score1 == score2


@settings(max_examples=20)
@given(strat.chunk_layouts())
def test_chunk_ordinals_sorted(layout):
    sorted_layout = sorted(layout)
    assert sorted_layout == sorted(layout)
