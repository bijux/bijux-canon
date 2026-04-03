# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Stack-safe, fully-lazy traversal of TreeDoc (end-of-Bijux RAG)."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator

from bijux_rag.core.rag_types import ChunkWithoutEmbedding, TextNode, TreeDoc

Path = tuple[int, ...]


def _make_chunk(node: TextNode, depth: int, path: Path) -> ChunkWithoutEmbedding:
    return ChunkWithoutEmbedding(
        doc_id=node.metadata.get("id", "unknown"),
        text=node.text,
        start=0,
        end=len(node.text),
        metadata={"depth": depth, "path": path},
    )


def assert_acyclic(tree: TreeDoc) -> None:
    """Raise ValueError if TreeDoc contains a cycle (by object identity)."""

    seen: set[int] = set()
    stack: list[TreeDoc] = [tree]
    while stack:
        node = stack.pop()
        nid = id(node)
        if nid in seen:
            raise ValueError("Cycle detected in TreeDoc")
        seen.add(nid)
        stack.extend(node.children)


def max_depth(tree: TreeDoc) -> int:
    """Iterative depth calculation (exported for analysis tools)."""

    max_d = 0
    stack: list[tuple[TreeDoc, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        max_d = max(max_d, depth)
        for child in node.children:
            stack.append((child, depth + 1))
    return max_d


def recursive_flatten(tree: TreeDoc) -> Iterator[ChunkWithoutEmbedding]:
    """Reference spec (beautiful, but not stack-safe on deep chains)."""

    def go(node: TreeDoc, *, depth: int, path: Path) -> Iterator[ChunkWithoutEmbedding]:
        yield _make_chunk(node.node, depth, path)
        for i, child in enumerate(node.children):
            yield from go(child, depth=depth + 1, path=path + (i,))

    yield from go(tree, depth=0, path=())


def iter_flatten(tree: TreeDoc) -> Iterator[ChunkWithoutEmbedding]:
    """Simple explicit-stack preorder traversal (stack-safe, but more allocations on deep chains)."""

    seen: set[int] = set()
    stack: deque[tuple[TreeDoc, int, Path]] = deque([(tree, 0, ())])
    while stack:
        node, depth, path = stack.pop()
        nid = id(node)
        if nid in seen:
            raise ValueError("Cycle detected in TreeDoc")
        seen.add(nid)
        yield _make_chunk(node.node, depth, path)
        for i in range(len(node.children) - 1, -1, -1):
            stack.append((node.children[i], depth + 1, path + (i,)))


def iter_flatten_buffered(tree: TreeDoc) -> Iterator[ChunkWithoutEmbedding]:
    """Allocation-bounded preorder traversal (production default).

    Traversal maintains path using a single mutable list; a path tuple is created
    only for emitted chunks' metadata.
    """

    seen: set[int] = set()
    stack: deque[tuple[TreeDoc, int, int | None]] = deque([(tree, 0, None)])
    path: list[int] = []
    last_depth = 0

    while stack:
        node, depth, sib_idx = stack.pop()
        nid = id(node)
        if nid in seen:
            raise ValueError("Cycle detected in TreeDoc")
        seen.add(nid)

        if depth < last_depth:
            del path[depth:]
        if sib_idx is not None:
            if depth > len(path):
                path.append(sib_idx)
            else:
                path[depth - 1] = sib_idx
        last_depth = depth

        yield _make_chunk(node.node, depth, tuple(path[:depth]))

        for i in range(len(node.children) - 1, -1, -1):
            stack.append((node.children[i], depth + 1, i))


def flatten(tree: TreeDoc) -> Iterator[ChunkWithoutEmbedding]:
    """Single recommended entrypoint: stack-safe + fully lazy on finite acyclic trees."""

    return iter_flatten_buffered(tree)


def flatten_via_fold(tree: TreeDoc) -> Iterator[ChunkWithoutEmbedding]:
    """Educational: build chunks via a fold (consumes the full tree)."""

    from .folds import fold_tree_buffered

    def step(
        acc: list[ChunkWithoutEmbedding], node: TreeDoc, depth: int, path: Path
    ) -> list[ChunkWithoutEmbedding]:
        acc.append(_make_chunk(node.node, depth, path))
        return acc

    seed: list[ChunkWithoutEmbedding] = []
    chunks: list[ChunkWithoutEmbedding] = fold_tree_buffered(tree, seed, step)
    return iter(chunks)


__all__ = [
    "Path",
    "assert_acyclic",
    "max_depth",
    "flatten",
    "recursive_flatten",
    "iter_flatten",
    "iter_flatten_buffered",
    "flatten_via_fold",
]
