# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Tree folds and scans as safe recursion (end-of-Bijux RAG)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

from bijux_rag.core.rag_types import TreeDoc

R = TypeVar("R")
T = TypeVar("T")
A = TypeVar("A")

Path = tuple[int, ...]


def fold_tree(tree: TreeDoc, seed: R, combiner: Callable[[R, TreeDoc, int, Path], R]) -> R:
    """Iterative preorder fold with explicit stack."""

    acc = seed
    stack: deque[tuple[TreeDoc, int, Path, int]] = deque([(tree, 0, (), 0)])
    while stack:
        node, depth, path, child_idx = stack.pop()
        if child_idx == 0:
            acc = combiner(acc, node, depth, path)
        if child_idx < len(node.children):
            stack.append((node, depth, path, child_idx + 1))
            child = node.children[child_idx]
            stack.append((child, depth + 1, path + (child_idx,), 0))
    return acc


def fold_tree_buffered(tree: TreeDoc, seed: R, combiner: Callable[[R, TreeDoc, int, Path], R]) -> R:
    """Preorder fold with traversal-internal path buffering (production hot-path)."""

    acc = seed
    stack: deque[tuple[TreeDoc, int, int | None]] = deque([(tree, 0, None)])
    path: list[int] = []
    last_depth = 0

    while stack:
        node, depth, sib_idx = stack.pop()

        if depth < last_depth:
            del path[depth:]
        if sib_idx is not None:
            if depth > len(path):
                path.append(sib_idx)
            else:
                path[depth - 1] = sib_idx
        last_depth = depth

        acc = combiner(acc, node, depth, tuple(path[:depth]))

        for i in range(len(node.children) - 1, -1, -1):
            stack.append((node.children[i], depth + 1, i))

    return acc


def fold_tree_no_path(tree: TreeDoc, seed: R, combiner: Callable[[R, TreeDoc, int], R]) -> R:
    """Iterative fold variant when path is not needed (depth only)."""

    acc = seed
    stack: deque[tuple[TreeDoc, int, int]] = deque([(tree, 0, 0)])
    while stack:
        node, depth, child_idx = stack.pop()
        if child_idx == 0:
            acc = combiner(acc, node, depth)
        if child_idx < len(node.children):
            stack.append((node, depth, child_idx + 1))
            stack.append((node.children[child_idx], depth + 1, 0))
    return acc


def scan_tree(
    tree: TreeDoc, seed: R, combiner: Callable[[R, TreeDoc, int, Path], R]
) -> Iterator[R]:
    """Yield running accumulator after each node in preorder."""

    acc = seed
    stack: deque[tuple[TreeDoc, int, Path, int]] = deque([(tree, 0, (), 0)])
    while stack:
        node, depth, path, child_idx = stack.pop()
        if child_idx == 0:
            acc = combiner(acc, node, depth, path)
            yield acc
        if child_idx < len(node.children):
            stack.append((node, depth, path, child_idx + 1))
            child = node.children[child_idx]
            stack.append((child, depth + 1, path + (child_idx,), 0))


def linear_reduce(xs: Iterable[T], seed: A, fn: Callable[[A, T], A]) -> A:
    """Left fold over a linear iterable."""

    acc = seed
    for x in xs:
        acc = fn(acc, x)
    return acc


def linear_accumulate(xs: Iterable[T], seed: A, fn: Callable[[A, T], A]) -> Iterator[A]:
    """Yield running accumulators for a linear iterable (includes initial seed)."""

    acc = seed
    yield acc
    for x in xs:
        acc = fn(acc, x)
        yield acc


def fold_count_length_maxdepth(tree: TreeDoc) -> tuple[int, int, int]:
    def step(
        acc: tuple[int, int, int], node: TreeDoc, depth: int, path: Path
    ) -> tuple[int, int, int]:
        del path
        count, length, max_d = acc
        return (count + 1, length + len(node.node.text), max(max_d, depth))

    return fold_tree_buffered(tree, (0, 0, 0), step)


def scan_count_length_maxdepth(tree: TreeDoc) -> Iterator[tuple[int, int, int]]:
    def step(
        acc: tuple[int, int, int], node: TreeDoc, depth: int, path: Path
    ) -> tuple[int, int, int]:
        del path
        count, length, max_d = acc
        return (count + 1, length + len(node.node.text), max(max_d, depth))

    return scan_tree(tree, (0, 0, 0), step)


__all__ = [
    "Path",
    "fold_tree",
    "fold_tree_no_path",
    "fold_tree_buffered",
    "scan_tree",
    "linear_reduce",
    "linear_accumulate",
    "fold_count_length_maxdepth",
    "scan_count_length_maxdepth",
]
