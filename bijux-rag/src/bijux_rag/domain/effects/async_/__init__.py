# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: async effect descriptions and combinators (end-of-Bijux RAG).

This subpackage groups all async-first primitives:
- `AsyncPlan` (single async step as a pure description)
- `AsyncGen` (lazy async stream as a pure description)
- Bounded concurrency/backpressure, resilience, scheduling, and batching helpers
- Lifts to run the synchronous core inside async pipelines without "async creep"
"""

from .concurrency import (
    BackpressurePolicy,
    FairnessPolicy,
    RateLimitPolicy,
    async_gen_bounded_map,
    async_gen_fair_merge,
    async_gen_rate_limited,
)
from .plan import (
    AsyncAction,
    AsyncPlan,
    async_bind,
    async_from_result,
    async_gather,
    async_lift,
    async_map,
    async_pure,
    lift_sync,
    lift_sync_gen_with_executor,
    lift_sync_with_executor,
)
from .resilience import (
    Clock,
    FakeClock,
    FakeTimeout,
    ResilienceEnv,
    RetryPolicy,
    Sleep,
    SystemClock,
    TimeoutCtx,
    TimeoutPolicy,
    async_with_resilience,
    make_fake_timeout_ctx,
    make_test_resilience_env,
    resilient_mapper,
)
from .stream import (
    AsyncGen,
    ChunkPolicy,
    FakeSleeper,
    RealSleeper,
    Sleeper,
    async_gen_and_then,
    async_gen_chunk,
    async_gen_flat_map,
    async_gen_from_list,
    async_gen_gather,
    async_gen_map,
    async_gen_map_action,
    async_gen_return,
    async_gen_using,
    lift_async_item,
)

__all__ = [
    # plans
    "AsyncPlan",
    "AsyncAction",
    "async_pure",
    "async_from_result",
    "async_bind",
    "async_map",
    "async_lift",
    "async_gather",
    # streams
    "AsyncGen",
    "async_gen_return",
    "async_gen_from_list",
    "async_gen_map",
    "async_gen_map_action",
    "async_gen_and_then",
    "async_gen_flat_map",
    "async_gen_gather",
    "lift_async_item",
    "async_gen_using",
    # backpressure
    "BackpressurePolicy",
    "async_gen_bounded_map",
    # scheduling
    "RateLimitPolicy",
    "FairnessPolicy",
    "async_gen_rate_limited",
    "async_gen_fair_merge",
    # resilience
    "TimeoutCtx",
    "Clock",
    "SystemClock",
    "FakeClock",
    "FakeTimeout",
    "make_fake_timeout_ctx",
    "Sleep",
    "ResilienceEnv",
    "make_test_resilience_env",
    "RetryPolicy",
    "TimeoutPolicy",
    "async_with_resilience",
    "resilient_mapper",
    # chunking
    "Sleeper",
    "RealSleeper",
    "FakeSleeper",
    "ChunkPolicy",
    "async_gen_chunk",
    # lifts
    "lift_sync",
    "lift_sync_with_executor",
    "lift_sync_gen_with_executor",
]
