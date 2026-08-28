# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Base schemas for interface payloads."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Represents strict model."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


__all__ = ["StrictModel"]
