# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Functional programming utilities for ingest pipelines.

This package groups two related layers:
- Iterator and pipeline combinators with lightweight instrumentation helpers
- Type-driven utilities such as ADTs, functors, applicatives, and monoids
- Reader, State, and Writer helpers with composition and runtime toggles

Common helpers are re-exported at the package root for convenience.
Effect helpers live in `bijux_canon_ingest.fp.effects`.
"""

from __future__ import annotations

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
    # Reader/State/Writer and configurable pipeline helpers
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
