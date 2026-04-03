# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Impure edges and boundary adapters (end-of-Bijux RAG).

This package groups the parts of the project that perform I/O or interact with
the outside world (CLI, filesystem, JSON/MessagePack, Pydantic schemas).

Reusable edge adapters live in `bijux_rag.boundaries.adapters`.
"""

from .adapters.exception_bridge import (
    UnexpectedFailure,
    result_map_try,
    try_result,
    unexpected_fail,
    v_map_try,
    v_try,
)
from .app_config import AppConfig

__all__ = [
    "AppConfig",
    "try_result",
    "result_map_try",
    "v_try",
    "v_map_try",
    "UnexpectedFailure",
    "unexpected_fail",
]
