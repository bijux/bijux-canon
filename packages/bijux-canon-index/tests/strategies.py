# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy


def vectors() -> SearchStrategy[tuple[float, ...]]:
    return st.lists(
        st.floats(-10, 10, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=5,
    ).map(tuple)


def queries() -> SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda v: {"request_id": "q", "text": None, "vector": v, "top_k": 3},
        vectors(),
    )


def chunk_layouts() -> SearchStrategy[list[int]]:
    return st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=5)
