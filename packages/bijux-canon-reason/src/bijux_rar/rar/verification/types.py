# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Severity(StrEnum):
    error = "error"
    warning = "warning"
    info = "info"


class CheckResult(VModel):
    name: str
    passed: bool
    severity: Severity = Severity.error
    details: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
