# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from bijux_rag.pipelines.cli import deep_merge, parse_override


@given(
    a=st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=10),
    b=st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=10),
)
@settings(max_examples=100)
def test_deep_merge_right_bias_for_scalars(a: dict[str, int], b: dict[str, int]) -> None:
    merged = deep_merge(dict(a), dict(b))
    for k, v in a.items():
        if k not in b:
            assert merged[k] == v
    for k, v in b.items():
        assert merged[k] == v


def test_parse_override_nested() -> None:
    assert parse_override("a.b.c=1") == {"a": {"b": {"c": 1}}}
    assert parse_override("flag=true") == {"flag": True}
    assert parse_override("x=hello") == {"x": "hello"}
