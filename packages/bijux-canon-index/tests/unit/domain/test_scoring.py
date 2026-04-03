# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import math

import pytest

from bijux_vex.core.errors import ValidationError
from bijux_vex.core.types import Result
from bijux_vex.domain.execution_requests import scoring


def test_l2_distance_deterministic():
    q = (0.0, 1.0, 2.0)
    t = (1.0, 1.0, 1.0)
    assert scoring.l2_distance(q, t) == 2.0
    assert scoring.l2_distance(t, q) == 2.0


def test_cosine_similarity_rejects_zero_vector():
    with pytest.raises(ValidationError):
        scoring.cosine_similarity((0.0, 0.0), (1.0, 1.0))


def test_score_non_finite_rejected():
    with pytest.raises(ValidationError):
        scoring.l2_distance((math.inf,), (0.0,))


def test_tie_break_key_ordering():
    r1 = Result(
        request_id="q",
        document_id="d1",
        chunk_id="c1",
        vector_id="v1",
        artifact_id="i",
        score=0.5,
        rank=1,
    )
    r2 = Result(
        request_id="q",
        document_id="d1",
        chunk_id="c2",
        vector_id="v2",
        artifact_id="i",
        score=0.5,
        rank=2,
    )
    assert scoring.tie_break_key(r1) < scoring.tie_break_key(r2)
