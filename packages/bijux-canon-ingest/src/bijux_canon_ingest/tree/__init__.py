# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tree-safe recursion tools.

Public surface:
- Stack-safe preorder traversal (`flatten`, `iter_flatten_buffered`)
- Safe folds/scans (`fold_tree_buffered`, `scan_tree`, ...)

`TreeDoc` and `TextNode` live in `bijux_canon_ingest.core.types`.
"""

from __future__ import annotations

from ._traversal import (
    Path,
    assert_acyclic,
    flatten,
    flatten_via_fold,
    iter_flatten,
    iter_flatten_buffered,
    max_depth,
    recursive_flatten,
)
from .folds import (
    fold_count_length_maxdepth,
    fold_tree,
    fold_tree_buffered,
    fold_tree_no_path,
    linear_accumulate,
    linear_reduce,
    scan_count_length_maxdepth,
    scan_tree,
)

__all__ = [
    "Path",
    "assert_acyclic",
    "max_depth",
    "flatten",
    "recursive_flatten",
    "iter_flatten",
    "iter_flatten_buffered",
    "flatten_via_fold",
    "fold_tree",
    "fold_tree_no_path",
    "fold_tree_buffered",
    "scan_tree",
    "linear_reduce",
    "linear_accumulate",
    "fold_count_length_maxdepth",
    "scan_count_length_maxdepth",
]
