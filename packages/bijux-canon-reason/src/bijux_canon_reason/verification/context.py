# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Context helpers for verification support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_reason.core.types import Plan, Trace


@dataclass(frozen=True)
class VerificationContext:
    """Represents verification context."""
    trace: Trace
    plan: Plan
    artifacts_dir: Path | None


__all__ = ["VerificationContext"]
