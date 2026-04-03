# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: cross-cutting policies and boundary helpers (end-of-Bijux RAG).

This package groups the non-domain-specific building blocks that shape how
pipelines behave at the edges:
- breakers: short-circuiting / circuit breakers over Result streams
- retries: pure retry engine with injectable policies
- memo: memoization utilities and a small disk cache
- resources: context-manager helpers for generator cleanup
- reports: structured error aggregation/reporting
"""

from __future__ import annotations

from .breakers import (
    BreakInfo,
    circuit_breaker_count_emit,
    circuit_breaker_count_truncate,
    circuit_breaker_pred_emit,
    circuit_breaker_pred_truncate,
    circuit_breaker_rate_emit,
    circuit_breaker_rate_truncate,
    short_circuit_on_err_emit,
    short_circuit_on_err_truncate,
)
from .memo import DiskCache, content_hash_key, lru_cache_custom, memoize_keyed
from .reports import ErrGroup, ErrReport, fold_error_counts, fold_error_report, report_to_jsonable
from .resources import auto_close, managed_stream, nested_managed, with_resource_stream
from .retries import (
    RetryCtx,
    RetryDecision,
    exp_policy,
    fixed_policy,
    is_retriable_errinfo,
    restore_input_order,
    retry_map_iter,
)

__all__ = [
    # breakers
    "BreakInfo",
    "short_circuit_on_err_emit",
    "short_circuit_on_err_truncate",
    "circuit_breaker_rate_emit",
    "circuit_breaker_rate_truncate",
    "circuit_breaker_count_emit",
    "circuit_breaker_count_truncate",
    "circuit_breaker_pred_emit",
    "circuit_breaker_pred_truncate",
    # retries
    "RetryCtx",
    "RetryDecision",
    "retry_map_iter",
    "fixed_policy",
    "exp_policy",
    "is_retriable_errinfo",
    "restore_input_order",
    # memo
    "lru_cache_custom",
    "memoize_keyed",
    "DiskCache",
    "content_hash_key",
    # resources
    "with_resource_stream",
    "managed_stream",
    "nested_managed",
    "auto_close",
    # reports
    "ErrGroup",
    "ErrReport",
    "fold_error_counts",
    "fold_error_report",
    "report_to_jsonable",
]
