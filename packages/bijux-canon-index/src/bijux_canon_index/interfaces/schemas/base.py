# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):  # type: ignore[misc]
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


__all__ = ["StrictModel"]
