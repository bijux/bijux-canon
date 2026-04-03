# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Core pipelines for the end-of-Bijux RAG codebase.

Bijux RAG established the pure, configurable API shapes.
Bijux RAG extends the project with streaming helpers (boundedness, grouping,
fan-in/out, time-aware pacing, and tracing) while preserving the Bijux RAG
behaviour when you materialize at the edge.

Bijux RAG adds stack-safe tree traversal + folds, richer Result/Option types,
memoization, per-record error handling, breakers, retries, resource safety, and
structured error reporting for streaming pipelines.

Bijux RAG introduces a type-driven toolkit (`bijux_rag.fp`) alongside
this RAG-focused package (`bijux_rag.rag`).
"""

from __future__ import annotations

from bijux_rag.policies.breakers import (
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
from bijux_rag.policies.memo import DiskCache, content_hash_key, lru_cache_custom, memoize_keyed
from bijux_rag.policies.reports import (
    ErrGroup,
    ErrReport,
    fold_error_counts,
    fold_error_report,
    report_to_jsonable,
)
from bijux_rag.policies.resources import (
    auto_close,
    managed_stream,
    nested_managed,
    with_resource_stream,
)
from bijux_rag.policies.retries import (
    RetryCtx,
    RetryDecision,
    exp_policy,
    fixed_policy,
    is_retriable_errinfo,
    restore_input_order,
    retry_map_iter,
)
from bijux_rag.result import (
    NONE,
    Err,
    ErrInfo,
    NoneVal,
    Ok,
    Option,
    Result,
    ResultsBoth,
    Some,
    all_ok_fail_fast,
    bind_option,
    bind_result,
    collect_both,
    filter_err,
    filter_ok,
    fold_results_collect_errs,
    fold_results_collect_errs_capped,
    fold_results_fail_fast,
    fold_until_error_rate,
    is_err,
    is_none,
    is_ok,
    is_some,
    make_errinfo,
    map_err,
    map_option,
    map_result,
    map_result_iter,
    option_from_nullable,
    option_to_nullable,
    par_try_map_iter,
    partition_results,
    recover,
    recover_iter,
    recover_result_iter,
    result_and_then,
    result_map,
    split_results_to_sinks,
    split_results_to_sinks_guarded,
    tap_err,
    tap_ok,
    to_option,
    try_map_iter,
    unwrap_or,
    unwrap_or_else,
)
from bijux_rag.streaming import multicast, throttle
from bijux_rag.streaming import trace_iter as _trace_iter
from bijux_rag.tree import (
    assert_acyclic,
    flatten,
    flatten_via_fold,
    fold_count_length_maxdepth,
    fold_tree,
    fold_tree_buffered,
    fold_tree_no_path,
    iter_flatten,
    iter_flatten_buffered,
    linear_accumulate,
    linear_reduce,
    max_depth,
    recursive_flatten,
    scan_count_length_maxdepth,
    scan_tree,
)

from .chunking import gen_chunk_doc, gen_chunk_spans, gen_overlapping_chunks, sliding_windows
from .rag_api import (
    full_rag_api,
    full_rag_api_docs,
    full_rag_api_path,
    iter_chunks_from_cleaned,
    iter_rag,
    iter_rag_core,
)
from .streaming_rag import (
    gen_bounded_chunks,
    gen_grouped_chunks,
    gen_stream_deduped,
    gen_stream_embedded,
    safe_rag_pipeline,
    stream_chunks,
)

__all__ = [
    # Bijux RAG: Tree traversal + folds
    "assert_acyclic",
    "flatten",
    "recursive_flatten",
    "iter_flatten",
    "iter_flatten_buffered",
    "flatten_via_fold",
    "max_depth",
    "fold_tree",
    "fold_tree_no_path",
    "fold_tree_buffered",
    "scan_tree",
    "linear_reduce",
    "linear_accumulate",
    "fold_count_length_maxdepth",
    "scan_count_length_maxdepth",
    # Bijux RAG: Result/Option + structured errors
    "Result",
    "Ok",
    "Err",
    "ErrInfo",
    "make_errinfo",
    "is_ok",
    "is_err",
    "map_result",
    "map_err",
    "bind_result",
    "recover",
    "unwrap_or",
    "to_option",
    "Option",
    "Some",
    "NoneVal",
    "NONE",
    "is_some",
    "is_none",
    "map_option",
    "bind_option",
    "unwrap_or_else",
    "option_from_nullable",
    "option_to_nullable",
    "map_result_iter",
    "filter_ok",
    "filter_err",
    "partition_results",
    "result_map",
    "result_and_then",
    # Bijux RAG: Result streaming combinators
    "try_map_iter",
    "par_try_map_iter",
    "tap_ok",
    "tap_err",
    "recover_iter",
    "recover_result_iter",
    "split_results_to_sinks",
    "split_results_to_sinks_guarded",
    # Bijux RAG: Aggregation
    "ResultsBoth",
    "fold_results_fail_fast",
    "fold_results_collect_errs",
    "fold_results_collect_errs_capped",
    "fold_until_error_rate",
    "all_ok_fail_fast",
    "collect_both",
    # Bijux RAG: Breakers
    "BreakInfo",
    "short_circuit_on_err_emit",
    "short_circuit_on_err_truncate",
    "circuit_breaker_rate_emit",
    "circuit_breaker_rate_truncate",
    "circuit_breaker_count_emit",
    "circuit_breaker_count_truncate",
    "circuit_breaker_pred_emit",
    "circuit_breaker_pred_truncate",
    # Bijux RAG: Resource safety
    "with_resource_stream",
    "managed_stream",
    "nested_managed",
    "auto_close",
    # Bijux RAG: Retries
    "RetryCtx",
    "RetryDecision",
    "retry_map_iter",
    "fixed_policy",
    "exp_policy",
    "is_retriable_errinfo",
    "restore_input_order",
    # Bijux RAG: Memoization
    "lru_cache_custom",
    "memoize_keyed",
    "DiskCache",
    "content_hash_key",
    # Bijux RAG: Reports
    "ErrGroup",
    "ErrReport",
    "fold_error_counts",
    "fold_error_report",
    "report_to_jsonable",
    "_trace_iter",
    "gen_chunk_doc",
    "gen_chunk_spans",
    "gen_overlapping_chunks",
    "sliding_windows",
    "gen_grouped_chunks",
    "stream_chunks",
    "gen_stream_embedded",
    "gen_stream_deduped",
    "gen_bounded_chunks",
    "safe_rag_pipeline",
    "multicast",
    "throttle",
    "iter_rag",
    "iter_rag_core",
    "iter_chunks_from_cleaned",
    "full_rag_api",
    "full_rag_api_docs",
    "full_rag_api_path",
]
