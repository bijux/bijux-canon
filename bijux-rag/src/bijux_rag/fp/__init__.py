# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Functional programming utilities for the end-of-Bijux RAG codebase.

This package groups two related layers:
- Bijux RAG–03: small iterator/pipeline combinators and instrumentation helpers.
- Bijux RAG: type-driven utilities (ADTs, functors, applicatives, monoids, etc.).
- Bijux RAG: monadic programming (Reader/State/Writer), layering helpers, and configurable pipelines.

Bijux RAG–03 helpers are re-exported at the package root for convenience.
Bijux RAG functionality is organized into submodules (e.g. `functor`,
`validation`, `monoid`). Bijux RAG effect helpers live in `bijux_rag.fp.effects`.
"""

from .combinators import (
    FakeTime,
    StageInstrumentation,
    compose,
    ffilter,
    flatmap,
    flow,
    fmap,
    identity,
    instrument_stage,
    pipe,
    probe,
    producer_pipeline,
    tee,
)
from .effects import (
    Reader,
    State,
    Writer,
    ask,
    asks,
    censor,
    get,
    listen,
    local,
    modify,
    put,
    run_state,
    run_writer,
    tell,
    tell_many,
    toggle_logging,
    toggle_metrics,
    toggle_validation,
    transpose_option_result,
    transpose_result_option,
    wr_and_then,
    wr_map,
    wr_pure,
)

__all__ = [
    "identity",
    "compose",
    "producer_pipeline",
    "flow",
    "pipe",
    "fmap",
    "ffilter",
    "flatmap",
    "tee",
    "probe",
    "StageInstrumentation",
    "instrument_stage",
    "FakeTime",
    # Bijux RAG: monads + layering + configurable pipelines
    "Reader",
    "ask",
    "asks",
    "local",
    "State",
    "get",
    "put",
    "modify",
    "run_state",
    "Writer",
    "tell",
    "tell_many",
    "listen",
    "censor",
    "run_writer",
    "wr_pure",
    "wr_map",
    "wr_and_then",
    "transpose_result_option",
    "transpose_option_result",
    "toggle_validation",
    "toggle_logging",
    "toggle_metrics",
]
