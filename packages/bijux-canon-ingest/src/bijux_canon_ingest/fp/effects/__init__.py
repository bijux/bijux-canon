# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Effect-encoding utilities for ingest pipelines.

This subpackage groups small-monad and effect helpers:
- Reader: explicit, injectable configuration
- State: explicit threaded state
- Writer: pure log/metrics accumulation
- Layering helpers (no monad transformers)
- Runtime-configurable pipeline toggles

`IOPlan` and related wrappers live under `bijux_canon_ingest.domain.effects`
as domain-owned effect interfaces.
"""

from __future__ import annotations

from .configurable import toggle_logging, toggle_metrics, toggle_validation
from .layering import transpose_option_result, transpose_result_option
from .reader import Reader, ask, asks, local
from .reader import pure as reader_pure
from .state import State, get, modify, put, run_state
from .state import pure as state_pure
from .writer import (
    Writer,
    censor,
    listen,
    run_writer,
    tell,
    tell_many,
    wr_and_then,
    wr_map,
    wr_pure,
)
from .writer import (
    pure as writer_pure,
)

__all__ = [
    # Reader
    "Reader",
    "reader_pure",
    "ask",
    "asks",
    "local",
    # State
    "State",
    "state_pure",
    "get",
    "put",
    "modify",
    "run_state",
    # Writer
    "Writer",
    "writer_pure",
    "tell",
    "tell_many",
    "listen",
    "censor",
    "run_writer",
    "wr_pure",
    "wr_map",
    "wr_and_then",
    # Layering helpers
    "transpose_result_option",
    "transpose_option_result",
    # Configurable pipelines
    "toggle_validation",
    "toggle_logging",
    "toggle_metrics",
]
