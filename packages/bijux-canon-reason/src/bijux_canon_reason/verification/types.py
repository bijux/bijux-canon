# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Types helpers for verification support."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VModel(BaseModel):
    """Represents vmodel."""
    model_config = ConfigDict(frozen=True, extra="forbid")


class Severity(StrEnum):
    """Enumeration of severity."""
    error = "error"
    warning = "warning"
    info = "info"


class CheckResult(VModel):
    """Represents check result."""
    name: str
    passed: bool
    severity: Severity = Severity.error
    details: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
