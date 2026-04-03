# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from hypothesis import given

from bijux_rag.tree import (
    flatten,
    fold_count_length_maxdepth,
    fold_tree,
    fold_tree_buffered,
    fold_tree_no_path,
)
from tests.strategies import tree_strategy


def recursive_fold(tree, seed, combiner, *, depth: int = 0, path: tuple[int, ...] = ()):
    acc = combiner(seed, tree, depth, path)
    for i, child in enumerate(tree.children):
        acc = recursive_fold(child, acc, combiner, depth=depth + 1, path=path + (i,))
    return acc


def step_count_len_maxd(
    acc: tuple[int, int, int], tree, depth: int, path: tuple[int, ...]
) -> tuple[int, int, int]:
    del path
    count, length, max_d = acc
    return (count + 1, length + len(tree.node.text), max(max_d, depth))


@given(tree=tree_strategy())
def test_fold_vs_recursive_equivalence(tree) -> None:
    rec = recursive_fold(tree, (0, 0, 0), step_count_len_maxd)
    buf = fold_tree_buffered(tree, (0, 0, 0), step_count_len_maxd)
    assert rec == buf


@given(tree=tree_strategy())
def test_fusion_equivalence(tree) -> None:
    fused = fold_count_length_maxdepth(tree)
    count = fold_tree_no_path(tree, 0, lambda a, _n, _d: a + 1)
    length = fold_tree_no_path(tree, 0, lambda a, n, _d: a + len(n.node.text))
    max_d = fold_tree_no_path(tree, 0, lambda a, _n, d: max(a, d))
    assert fused == (count, length, max_d)


@given(tree=tree_strategy())
def test_fold_preorder_matches_flatten(tree) -> None:
    order_via_fold: list[tuple[int, ...]] = []

    def step(_, _n, _d, p):
        order_via_fold.append(p)
        return None

    fold_tree(tree, None, step)
    order_via_flatten = [c.metadata["path"] for c in flatten(tree)]
    assert order_via_fold == order_via_flatten
