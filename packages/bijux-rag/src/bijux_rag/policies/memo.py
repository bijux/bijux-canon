# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Memoization and caching for pure functions (end-of-Bijux RAG)."""

from __future__ import annotations

import functools
import hashlib
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Hashable, Optional, ParamSpec, TypeVar, cast

from bijux_rag.core.rag_types import ChunkWithoutEmbedding

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")
P = ParamSpec("P")
R = TypeVar("R")


def lru_cache_custom(
    maxsize: Optional[int] = 512,
) -> Callable[[Callable[..., V]], Callable[..., V]]:
    """Drop-in wrapper around functools.lru_cache with a project default maxsize."""

    return functools.lru_cache(maxsize=maxsize)


@dataclass
class CacheInfo:
    hits: int = 0
    misses: int = 0
    evictions: int = 0


def memoize_keyed(
    key_fn: Callable[P, K],
    *,
    maxsize: Optional[int] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Memoize a pure function by an explicit key function.

    This caches by key_fn(*args, **kwargs) while still calling fn(*args, **kwargs).
    Thread-safe; exposes best-effort cache_info() / cache_clear().
    """

    info = CacheInfo()
    lock = threading.RLock()

    if maxsize is not None:
        cache: OrderedDict[K, Any] = OrderedDict()

        def decorator(fn: Callable[P, R]) -> Callable[P, R]:
            @functools.wraps(fn)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                k = key_fn(*args, **kwargs)
                with lock:
                    if k in cache:
                        info.hits += 1
                        cache.move_to_end(k)
                        return cast(R, cache[k])
                    info.misses += 1

                v = fn(*args, **kwargs)

                with lock:
                    if len(cache) >= maxsize:
                        cache.popitem(last=False)
                        info.evictions += 1
                    cache[k] = v
                    cache.move_to_end(k)
                return v

            wrapped.cache_info = lambda: info  # type: ignore[attr-defined]
            wrapped.cache_clear = cache.clear  # type: ignore[attr-defined]
            return wrapped

        return decorator

    cache2: dict[K, Any] = {}

    def decorator_unbounded(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            k = key_fn(*args, **kwargs)
            with lock:
                if k in cache2:
                    info.hits += 1
                    return cast(R, cache2[k])

            v = fn(*args, **kwargs)
            with lock:
                if k not in cache2:
                    cache2[k] = v
                    info.misses += 1
            return v

        wrapped.cache_info = lambda: info  # type: ignore[attr-defined]
        wrapped.cache_clear = cache2.clear  # type: ignore[attr-defined]
        return wrapped

    return decorator_unbounded


class DiskCache:
    """Persistent, atomic, versioned disk cache.

    Keys are strings; values are arbitrary bytes (caller handles serialization).
    """

    def __init__(self, dirpath: str, namespace: str = "default", version: str = "v1") -> None:
        self.dir = Path(dirpath)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.prefix = f"{namespace}-{version}-"

    def _path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.dir / f"{self.prefix}{h}.bin"

    def get(self, key: str) -> Optional[bytes]:
        p = self._path(key)
        return p.read_bytes() if p.exists() else None

    def set(self, key: str, value: bytes) -> None:
        p = self._path(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(value)
        os.replace(tmp, p)


def content_hash_key(chunk: ChunkWithoutEmbedding, *, norm_version: str = "v1") -> str:
    """Deterministic content key (must match normalisation semantics)."""

    norm_text = " ".join(chunk.text.strip().lower().split())
    h = hashlib.blake2b(digest_size=32)
    h.update(norm_version.encode())
    h.update(b"\x00")
    h.update(norm_text.encode("utf-8"))
    return h.hexdigest()


__all__ = [
    "lru_cache_custom",
    "memoize_keyed",
    "CacheInfo",
    "DiskCache",
    "content_hash_key",
]
