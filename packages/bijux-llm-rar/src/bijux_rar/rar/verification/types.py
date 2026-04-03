# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Severity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


class CheckResult(VModel):
    name: str
    passed: bool
    severity: Severity = Severity.error
    details: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
