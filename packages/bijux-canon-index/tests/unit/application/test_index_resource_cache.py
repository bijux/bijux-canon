# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for bounded process-local immutable generation reuse."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import threading
from typing import cast

import pytest

from bijux_canon_index.application import IndexGeneration
from bijux_canon_index.application.index_resource_cache import (
    IndexGenerationResourceCache,
)


@dataclass
class _GenerationHandle:
    name: str
    close_count: int = 0

    def close(self) -> None:
        self.close_count += 1


def _generation(handle: _GenerationHandle) -> IndexGeneration:
    return cast(IndexGeneration, cast(object, handle))


def test_cache_loads_once_and_serializes_cross_thread_leases() -> None:
    cache = IndexGenerationResourceCache(
        cache_identity="sha256:workspace",
        maximum_entries=2,
    )
    handle = _GenerationHandle("generation-a")
    loads = 0

    def load() -> IndexGeneration:
        nonlocal loads
        loads += 1
        return _generation(handle)

    def use(_ordinal: int) -> str:
        with cache.lease(
            generation_id="sha256:generation-a",
            version=(("generation.json", 1, 10, 20),),
            loader=load,
        ) as generation:
            return cast(_GenerationHandle, cast(object, generation)).name

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert tuple(executor.map(use, range(32))) == ("generation-a",) * 32

    report = cache.report()
    assert loads == 1
    assert report.load_count == 1
    assert report.last_access_status == "warm"
    assert report.miss_count == 1
    assert report.hit_count == 31
    assert report.resident_entries == 1
    assert report.maximum_entries == 2
    assert handle.close_count == 0


def test_cache_invalidates_changed_identity_and_evicts_to_its_bound() -> None:
    cache = IndexGenerationResourceCache(
        cache_identity="sha256:workspace",
        maximum_entries=1,
    )
    first = _GenerationHandle("first")
    changed = _GenerationHandle("changed")
    second = _GenerationHandle("second")

    with cache.lease(
        generation_id="sha256:generation-a",
        version=(("generation.json", 1, 10, 20),),
        loader=lambda: _generation(first),
    ):
        pass
    with cache.lease(
        generation_id="sha256:generation-a",
        version=(("generation.json", 1, 11, 21),),
        loader=lambda: _generation(changed),
    ):
        pass
    assert first.close_count == 1

    with cache.lease(
        generation_id="sha256:generation-b",
        version=(("generation.json", 2, 10, 20),),
        loader=lambda: _generation(second),
    ):
        pass

    report = cache.report()
    assert changed.close_count == 1
    assert report.resident_generation_ids == ("sha256:generation-b",)
    assert report.resident_entries == 1
    assert report.invalidation_count == 2
    assert report.eviction_count == 1
    assert report.load_count == 3
    assert report.last_access_status == "cold"

    cache.close()
    assert second.close_count == 1
    with pytest.raises(RuntimeError, match="cache is closed"):
        with cache.lease(
            generation_id="sha256:generation-c",
            version=(("generation.json", 3, 10, 20),),
            loader=lambda: _generation(_GenerationHandle("unexpected")),
        ):
            pass


def test_changed_generation_waits_for_active_lease_before_replacement() -> None:
    cache = IndexGenerationResourceCache(
        cache_identity="sha256:workspace",
        maximum_entries=1,
    )
    first = _GenerationHandle("first")
    changed = _GenerationHandle("changed")
    first_acquired = threading.Event()
    release_first = threading.Event()
    changed_loader_started = threading.Event()
    changed_loads = 0

    def hold_first() -> None:
        with cache.lease(
            generation_id="sha256:generation-a",
            version=(("generation.json", 1, 10, 20),),
            loader=lambda: _generation(first),
        ):
            first_acquired.set()
            assert release_first.wait(timeout=2.0)

    def load_changed() -> IndexGeneration:
        nonlocal changed_loads
        changed_loads += 1
        changed_loader_started.set()
        return _generation(changed)

    def use_changed() -> None:
        with cache.lease(
            generation_id="sha256:generation-a",
            version=(("generation.json", 1, 11, 21),),
            loader=load_changed,
        ):
            pass

    with ThreadPoolExecutor(max_workers=3) as executor:
        first_future = executor.submit(hold_first)
        assert first_acquired.wait(timeout=2.0)
        changed_future = executor.submit(use_changed)
        second_changed_future = executor.submit(use_changed)
        assert not changed_loader_started.wait(timeout=0.05)
        release_first.set()
        first_future.result(timeout=2.0)
        changed_future.result(timeout=2.0)
        second_changed_future.result(timeout=2.0)

    assert changed_loader_started.is_set()
    assert changed_loads == 1
    assert first.close_count == 1
    assert cache.report().load_count == 2
