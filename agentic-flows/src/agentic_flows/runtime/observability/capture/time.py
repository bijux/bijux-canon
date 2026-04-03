# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/capture/time.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now_deterministic(step_index: int) -> str:
    """Execute utc_now_deterministic and enforce its contract."""
    base = datetime(1970, 1, 1, tzinfo=UTC)
    timestamp = base + timedelta(seconds=step_index)
    return timestamp.isoformat().replace("+00:00", "Z")
