# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from hypothesis import strategies as st


def vectors():
    return st.lists(
        st.floats(-10, 10, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=5,
    ).map(tuple)


def queries():
    return st.builds(
        lambda v: {"request_id": "q", "text": None, "vector": v, "top_k": 3},
        vectors(),
    )


def chunk_layouts():
    return st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=5)
