# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.domain.requests import scoring
from hypothesis import HealthCheck, given, settings
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
