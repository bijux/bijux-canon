# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Boundary exception helpers for bijux-canon-ingest."""

from __future__ import annotations

from .exception_bridge import (
    UnexpectedFailure,
    result_map_try,
    try_result,
    unexpected_fail,
    v_map_try,
    v_try,
)

__all__ = [
    "try_result",
    "result_map_try",
    "v_try",
    "v_map_try",
    "UnexpectedFailure",
    "unexpected_fail",
]
