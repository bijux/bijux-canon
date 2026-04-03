# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from itertools import islice

import pytest
from hypothesis import given

from bijux_rag.tree import flatten, iter_flatten, iter_flatten_buffered, recursive_flatten
from tests.strategies import deep_chain_strategy, tree_strategy


@given(tree=tree_strategy())
def test_equivalence_all_variants(tree) -> None:
    rec = list(recursive_flatten(tree))
    simple = list(iter_flatten(tree))
    buf = list(iter_flatten_buffered(tree))
    prod = list(flatten(tree))
    assert rec == simple == buf == prod


@given(tree=deep_chain_strategy(depth=5000))
def test_stack_safety_and_prefix_laziness_extreme(tree) -> None:
    with pytest.raises(RecursionError):
        list(recursive_flatten(tree))

    it = flatten(tree)
    assert len(list(islice(it, 100))) == 100
    assert len(list(it)) == 4900


@given(tree=tree_strategy())
def test_metadata_and_order_invariants(tree) -> None:
    chunks = list(flatten(tree))
    paths = [c.metadata["path"] for c in chunks]
    depths = [c.metadata["depth"] for c in chunks]

    assert all(isinstance(p, tuple) for p in paths)
    assert all(isinstance(d, int) for d in depths)
    assert all(d == len(p) for d, p in zip(depths, paths))
    assert len(set(paths)) == len(paths)
    assert paths == sorted(paths)  # preorder monotonicity for tuple paths

    for p, q in zip(paths, paths[1:]):
        if len(p) == len(q) and len(p) > 0 and p[:-1] == q[:-1]:
            assert p[-1] < q[-1]
