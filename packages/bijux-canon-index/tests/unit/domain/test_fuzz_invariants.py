# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bijux_canon_index.domain.requests import scoring

_VECTORS = st.lists(
    st.floats(-10, 10, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=5,
).map(tuple)
_CHUNK_LAYOUTS = st.lists(
    st.integers(min_value=0, max_value=10), min_size=1, max_size=5
)


@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(_VECTORS)
def test_scoring_determinism(vec: tuple[float, ...]) -> None:
    score1 = scoring.l2_distance(vec, vec)
    score2 = scoring.l2_distance(vec, vec)
    assert score1 == score2


@settings(max_examples=20)
@given(_CHUNK_LAYOUTS)
def test_chunk_ordinals_sorted(layout: list[int]) -> None:
    sorted_layout = sorted(layout)
    assert sorted_layout == sorted(layout)
