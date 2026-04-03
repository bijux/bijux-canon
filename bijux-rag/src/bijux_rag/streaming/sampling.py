# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Sampling helpers for streams (Bijux RAG)."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar

from .types import Transform

T = TypeVar("T")


def make_sampler_bernoulli(rate: float, *, seed: int = 0) -> Transform[T, T]:
    """Probabilistic sampler with deterministic reuse (fresh RNG per call)."""

    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate must be in [0.0, 1.0]")

    def stage(items: Iterable[T]) -> Iterator[T]:
        rng = random.Random(seed)
        for item in items:
            if rng.random() < rate:
                yield item

    return stage


def make_sampler_periodic(k: int, *, offset: int = 0) -> Transform[T, T]:
    """Deterministic periodic sampler: yields every k-th item (with offset)."""

    if k <= 0:
        raise ValueError("k must be > 0")

    def stage(items: Iterable[T]) -> Iterator[T]:
        for i, item in enumerate(items):
            if (i - offset) % k == 0:
                yield item

    return stage


def make_sampler_stable(rate: float, *, key: Callable[[T], bytes]) -> Transform[T, T]:
    """Order-insensitive, cross-run stable sampler using a 64-bit blake2b threshold.

    Determinism is guaranteed across Python runs as long as `key(item)` is stable.
    """

    if not 0.0 <= rate <= 1.0:
        raise ValueError("rate must be in [0.0, 1.0]")

    denom = 2**64
    threshold = int(rate * denom)

    def stage(items: Iterable[T]) -> Iterator[T]:
        for item in items:
            digest = hashlib.blake2b(key(item), digest_size=8).digest()
            val = int.from_bytes(digest, "big")
            if val < threshold:
                yield item

    return stage


__all__ = ["make_sampler_bernoulli", "make_sampler_periodic", "make_sampler_stable"]
