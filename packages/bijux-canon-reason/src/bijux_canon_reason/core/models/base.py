# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Base helpers for core logic."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic import JsonValue as PydanticJsonValue

JsonValue = PydanticJsonValue


class StableModel(BaseModel):
    # validate_default enforces validators even for generated defaults
    """Represents stable model."""
    model_config = ConfigDict(
        frozen=True, extra="forbid", validate_default=True, populate_by_name=True
    )


__all__ = ["JsonValue", "StableModel"]
