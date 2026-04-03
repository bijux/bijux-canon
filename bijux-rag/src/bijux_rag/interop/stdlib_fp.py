# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 1: stdlib functional programming utilities (end-of-Bijux RAG).

These helpers are intentionally thin wrappers around the standard library.
They exist primarily for documentation/tests and to keep example snippets
consistent across modules.
"""

from __future__ import annotations

import operator
from collections.abc import Iterable, Iterator
from itertools import accumulate, chain, tee
from typing import TypeVar

T = TypeVar("T")


def merge_streams(*streams: Iterable[T]) -> Iterator[T]:
    """Lazily chain multiple iterables."""

    return chain(*streams)


def multicast_stream(stream: Iterable[T]) -> tuple[Iterator[T], Iterator[T]]:
    """Duplicate an iterable into two iterators (beware tee skew memory)."""

    a, b = tee(stream, 2)
    return a, b


def running_sum(nums: Iterable[int]) -> Iterator[int]:
    """Running fold via itertools.accumulate."""

    return accumulate(nums, operator.add)


__all__ = ["merge_streams", "multicast_stream", "running_sum"]
