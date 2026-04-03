# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from bijux_vex.bench.dataset import generate_dataset


def test_dataset_generator_is_deterministic() -> None:
    dataset_a = generate_dataset(size=16, dimension=8, query_count=4, seed=123)
    dataset_b = generate_dataset(size=16, dimension=8, query_count=4, seed=123)
    assert dataset_a.documents == dataset_b.documents
    assert dataset_a.vectors.tolist() == dataset_b.vectors.tolist()
    assert dataset_a.queries.tolist() == dataset_b.queries.tolist()
