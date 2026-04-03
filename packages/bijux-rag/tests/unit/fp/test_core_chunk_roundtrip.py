# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typing_extensions import assert_never

from bijux_rag.fp.core import (
    Chunk,
    ChunkState,
    Failure,
    Success,
    chunk_from_dict,
    chunk_state_from_dict,
    chunk_state_to_dict,
    chunk_to_dict,
    failure,
    make_chunk,
    success,
)

json_value = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda inner: st.lists(inner, max_size=5) | st.dictionaries(st.text(), inner, max_size=5),
    max_leaves=25,
)


@given(
    text=st.text(),
    path=st.lists(st.integers(), max_size=10).map(tuple),
    meta=st.dictionaries(st.text(), json_value, max_size=10),
)
def test_chunk_immutability(text: str, path: tuple[int, ...], meta: dict[str, object]) -> None:
    chunk = make_chunk(text=text, path=path, metadata=meta)  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        chunk.text = "mutated"  # type: ignore[misc]


@given(meta=st.dictionaries(st.text(), st.integers(), max_size=20))
def test_chunk_metadata_order_independent(meta: dict[str, int]) -> None:
    c1 = make_chunk(text="t", path=(), metadata=meta)
    c2 = make_chunk(text="t", path=(), metadata=dict(reversed(list(meta.items()))))
    assert c1 == c2
    assert hash(c1) == hash(c2)


@given(
    chunk=st.builds(
        make_chunk,
        text=st.text(),
        path=st.lists(st.integers(), max_size=10).map(tuple),
        metadata=st.dictionaries(st.text(), json_value, max_size=10),
    )
)
def test_chunk_roundtrip(chunk: Chunk) -> None:
    j = chunk_to_dict(chunk)
    reloaded = chunk_from_dict(j)
    assert chunk == reloaded


@given(
    succ=st.builds(
        success,
        embedding=st.lists(st.floats(allow_nan=False, allow_infinity=False), max_size=10),
        metadata=st.dictionaries(st.text(), json_value, max_size=10),
    ),
    fail=st.builds(
        failure,
        code=st.text(min_size=1),
        msg=st.text(),
        attempt=st.integers(min_value=1, max_value=100),
    ),
)
def test_chunk_state_roundtrip(succ: Success, fail: Failure) -> None:
    for state in (succ, fail):
        j = chunk_state_to_dict(state)
        reloaded = chunk_state_from_dict(j)
        assert state == reloaded


@given(
    state=st.one_of(
        st.builds(
            success,
            embedding=st.lists(st.floats(allow_nan=False, allow_infinity=False), max_size=3),
            metadata=st.dictionaries(st.text(), st.integers(), max_size=3),
        ),
        st.builds(
            failure,
            code=st.text(min_size=1),
            msg=st.text(),
            attempt=st.integers(min_value=1, max_value=10),
        ),
    )
)
def test_chunk_state_is_closed_union(state: ChunkState) -> None:
    assert isinstance(state, (Success, Failure))


@dataclass(frozen=True, slots=True, kw_only=True)
class TextNode:
    kind: Literal["text"] = "text"
    content: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionNode:
    kind: Literal["section"] = "section"
    title: str
    children: tuple["Node", ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ListNode:
    kind: Literal["list"] = "list"
    items: tuple["Node", ...]


Node = TextNode | SectionNode | ListNode


@given(
    node=st.recursive(
        st.builds(TextNode, content=st.text()),
        lambda children: st.one_of(
            st.builds(SectionNode, title=st.text(), children=children),
            st.builds(ListNode, items=children),
        ),
        max_leaves=20,
    )
)
def test_node_exhaustive_match(node: Node) -> None:
    def dummy(n: Node) -> int:
        match n:
            case TextNode():
                return 0
            case SectionNode():
                return 1
            case ListNode():
                return 2
        assert_never(n)

    dummy(node)
