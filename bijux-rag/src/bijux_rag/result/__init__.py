# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Result/Option and Result-stream utilities (end-of-Bijux RAG).

This package groups:
- `types`: Result/Option containers + ErrInfo
- `stream`: lazy combinators for Result iterables
- `folds`: aggregation folds over Result streams
"""

from __future__ import annotations

from .folds import (
    ResultsBoth,
    all_ok_fail_fast,
    collect_both,
    fold_results_collect_errs,
    fold_results_collect_errs_capped,
    fold_results_fail_fast,
    fold_until_error_rate,
)
from .stream import (
    filter_err,
    filter_ok,
    map_result_iter,
    par_try_map_iter,
    partition_results,
    recover_iter,
    recover_result_iter,
    split_results_to_sinks,
    split_results_to_sinks_guarded,
    tap_err,
    tap_ok,
    try_map_iter,
)
from .types import (
    NONE,
    Err,
    ErrInfo,
    NoneVal,
    Ok,
    Option,
    Result,
    Some,
    bind_option,
    bind_result,
    curry2,
    is_err,
    is_none,
    is_ok,
    is_some,
    liftA2,
    make_errinfo,
    map_err,
    map_option,
    map_result,
    option_from_nullable,
    option_to_nullable,
    recover,
    result_and_then,
    result_map,
    to_option,
    unwrap_or,
    unwrap_or_else,
)

__all__ = [
    # Result/Option types
    "Result",
    "Ok",
    "Err",
    "curry2",
    "liftA2",
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
    "result_map",
    "result_and_then",
    # Stream combinators
    "map_result_iter",
    "filter_ok",
    "filter_err",
    "partition_results",
    "try_map_iter",
    "par_try_map_iter",
    "tap_ok",
    "tap_err",
    "recover_iter",
    "recover_result_iter",
    "split_results_to_sinks",
    "split_results_to_sinks_guarded",
    # Folds / aggregation
    "ResultsBoth",
    "fold_results_fail_fast",
    "fold_results_collect_errs",
    "fold_results_collect_errs_capped",
    "fold_until_error_rate",
    "all_ok_fail_fast",
    "collect_both",
]
