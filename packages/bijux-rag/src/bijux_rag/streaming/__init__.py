# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: generic, domain-agnostic streaming utilities.

This package groups the Bijux RAG helpers by responsibility:
- composition / fencing
- fan-in / fan-out
- observability / sampling
- time-aware pacing
- groupby contiguity guards

RAG-specific streaming functions live in `bijux_rag.rag.streaming_rag`.
"""

from __future__ import annotations

from .compose import compose2_transforms, compose_transforms, fence_k, source_to_transform
from .contiguity import ensure_contiguous
from .fanin import as_source, make_chain, make_merge, make_roundrobin
from .fanout import fork2_lockstep, multicast, tap_prefix
from .observability import make_counter, make_peek, make_tap
from .sampling import make_sampler_bernoulli, make_sampler_periodic, make_sampler_stable
from .time import make_call_gate, make_rate_limit, make_throttle, make_timestamp, throttle
from .types import Lens, Source, TraceLens, Transform, trace_iter

__all__ = [
    # types + tracing
    "Source",
    "Transform",
    "Lens",
    "TraceLens",
    "trace_iter",
    # composition / fencing
    "fence_k",
    "compose2_transforms",
    "compose_transforms",
    "source_to_transform",
    # fan-in / fan-out
    "as_source",
    "make_chain",
    "make_roundrobin",
    "make_merge",
    "fork2_lockstep",
    "multicast",
    "tap_prefix",
    # grouping safety
    "ensure_contiguous",
    # observability / sampling
    "make_tap",
    "make_counter",
    "make_peek",
    "make_sampler_bernoulli",
    "make_sampler_periodic",
    "make_sampler_stable",
    # time-aware pacing (sync-only in Bijux RAG)
    "make_throttle",
    "throttle",
    "make_rate_limit",
    "make_timestamp",
    "make_call_gate",
]
