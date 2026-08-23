# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded process-local leases for verified immutable index generations."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import threading
from time import perf_counter

from bijux_canon_index.application.index_generation import IndexGeneration

GenerationVersion = tuple[tuple[str, int, int, int], ...]
GenerationLoader = Callable[[], IndexGeneration]


@dataclass(frozen=True, slots=True)
class IndexResourceCacheReport:
    """Content-safe cache state and lifecycle counters."""

    schema_version: str
    cache_identity: str
    maximum_entries: int
    resident_entries: int
    active_leases: int
    hit_count: int
    miss_count: int
    invalidation_count: int
    eviction_count: int
    load_count: int
    total_load_ms: float
    last_load_ms: float | None
    last_access_status: str
    resident_generation_ids: tuple[str, ...]


@dataclass(slots=True)
class _CachedGeneration:
    generation_id: str
    version: GenerationVersion
    generation: IndexGeneration
    loaded_ms: float
    access_ordinal: int
    active_leases: int = 0
    stale: bool = False
    query_lock: threading.RLock = field(default_factory=threading.RLock)


class IndexGenerationResourceCache:
    """Share a bounded number of verified read-only generations safely."""

    def __init__(self, *, cache_identity: str, maximum_entries: int = 2) -> None:
        if not cache_identity:
            raise ValueError("index resource cache identity must not be empty")
        if not 1 <= maximum_entries <= 16:
            raise ValueError("index resource cache entries must be within 1..16")
        self._cache_identity = cache_identity
        self._maximum_entries = maximum_entries
        self._entries: OrderedDict[str, _CachedGeneration] = OrderedDict()
        self._condition = threading.Condition(threading.RLock())
        self._closed = False
        self._ordinal = 0
        self._hit_count = 0
        self._miss_count = 0
        self._invalidation_count = 0
        self._eviction_count = 0
        self._load_count = 0
        self._total_load_ms = 0.0
        self._last_load_ms: float | None = None
        self._last_access_status = "cold"

    @contextmanager
    def lease(
        self,
        *,
        generation_id: str,
        version: GenerationVersion,
        loader: GenerationLoader,
    ) -> Iterator[IndexGeneration]:
        """Lease one verified generation, serializing access to its handles."""

        entry = self._acquire(
            generation_id=generation_id,
            version=version,
            loader=loader,
        )
        try:
            with entry.query_lock:
                yield entry.generation
        finally:
            self._release(entry)

    def invalidate(self, generation_id: str | None = None) -> None:
        """Invalidate one identity or every resident generation."""

        with self._condition:
            targets = [
                entry
                for identity, entry in self._entries.items()
                if generation_id is None or identity == generation_id
            ]
            for entry in targets:
                self._mark_stale(entry)
            self._condition.notify_all()

    def report(self) -> IndexResourceCacheReport:
        """Return current bounds and counters without exposing paths or content."""

        with self._condition:
            resident = tuple(
                entry.generation_id
                for entry in self._entries.values()
                if not entry.stale
            )
            return IndexResourceCacheReport(
                schema_version="bijux.canon.index.resource_cache.v1",
                cache_identity=self._cache_identity,
                maximum_entries=self._maximum_entries,
                resident_entries=len(resident),
                active_leases=sum(
                    entry.active_leases for entry in self._entries.values()
                ),
                hit_count=self._hit_count,
                miss_count=self._miss_count,
                invalidation_count=self._invalidation_count,
                eviction_count=self._eviction_count,
                load_count=self._load_count,
                total_load_ms=self._total_load_ms,
                last_load_ms=self._last_load_ms,
                last_access_status=self._last_access_status,
                resident_generation_ids=resident,
            )

    def close(self) -> None:
        """Refuse new leases and release idle resources deterministically."""

        with self._condition:
            self._closed = True
            for entry in tuple(self._entries.values()):
                self._mark_stale(entry)
            self._condition.notify_all()

    def _acquire(
        self,
        *,
        generation_id: str,
        version: GenerationVersion,
        loader: GenerationLoader,
    ) -> _CachedGeneration:
        with self._condition:
            invalidated = False
            while True:
                if self._closed:
                    raise RuntimeError("index resource cache is closed")
                existing = self._entries.get(generation_id)
                if existing is not None and not existing.stale:
                    if existing.version == version:
                        self._hit_count += 1
                        self._last_access_status = "warm"
                        self._touch(existing)
                        existing.active_leases += 1
                        return existing
                    self._mark_stale(existing)
                    invalidated = True
                    continue
                if existing is not None:
                    self._condition.wait()
                    continue
                if self._resident_count() >= self._maximum_entries:
                    if self._evict_one_idle():
                        continue
                    self._condition.wait()
                    continue
                self._miss_count += 1
                started = perf_counter()
                generation = loader()
                loaded_ms = (perf_counter() - started) * 1000.0
                self._ordinal += 1
                entry = _CachedGeneration(
                    generation_id=generation_id,
                    version=version,
                    generation=generation,
                    loaded_ms=loaded_ms,
                    access_ordinal=self._ordinal,
                    active_leases=1,
                )
                self._entries[generation_id] = entry
                self._entries.move_to_end(generation_id)
                self._load_count += 1
                self._total_load_ms += loaded_ms
                self._last_load_ms = loaded_ms
                self._last_access_status = "invalidated" if invalidated else "cold"
                return entry

    def _release(self, entry: _CachedGeneration) -> None:
        with self._condition:
            entry.active_leases -= 1
            if entry.active_leases < 0:
                raise RuntimeError("index resource cache lease count underflow")
            if entry.stale and entry.active_leases == 0:
                self._close_entry(entry)
            self._condition.notify_all()

    def _resident_count(self) -> int:
        return len(self._entries)

    def _touch(self, entry: _CachedGeneration) -> None:
        self._ordinal += 1
        entry.access_ordinal = self._ordinal
        self._entries.move_to_end(entry.generation_id)

    def _evict_one_idle(self) -> bool:
        for entry in tuple(self._entries.values()):
            if not entry.stale and entry.active_leases == 0:
                self._eviction_count += 1
                self._mark_stale(entry)
                return True
        return False

    def _mark_stale(self, entry: _CachedGeneration) -> None:
        if not entry.stale:
            entry.stale = True
            self._invalidation_count += 1
        if entry.active_leases == 0:
            self._close_entry(entry)

    def _close_entry(self, entry: _CachedGeneration) -> None:
        selected = self._entries.get(entry.generation_id)
        if selected is entry:
            self._entries.pop(entry.generation_id, None)
        entry.generation.close()


def generation_version(path: Path) -> GenerationVersion:
    """Return cheap mutation-sensitive file identities for one generation."""

    result = []
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        if child.is_file():
            stat = child.stat()
            result.append((child.name, stat.st_ino, stat.st_size, stat.st_mtime_ns))
    if not result:
        raise FileNotFoundError(path)
    return tuple(result)


__all__ = [
    "GenerationVersion",
    "IndexGenerationResourceCache",
    "IndexResourceCacheReport",
    "generation_version",
]
