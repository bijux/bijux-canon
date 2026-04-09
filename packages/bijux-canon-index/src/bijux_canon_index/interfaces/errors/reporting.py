# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Observability hooks for interface-layer failures."""

from __future__ import annotations

from bijux_canon_index.core import errors
from bijux_canon_index.infra.metrics import METRICS

_BACKEND_FAILURE_TYPES = (
    errors.BackendUnavailableError,
    errors.BackendCapabilityError,
    errors.BackendDivergenceError,
)


def record_failure(exc: Exception) -> None:
    """Record failure."""
    if isinstance(exc, _BACKEND_FAILURE_TYPES):
        METRICS.increment("backend_failures_total", 1)


__all__ = ["record_failure"]
