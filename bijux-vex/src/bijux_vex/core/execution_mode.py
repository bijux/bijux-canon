# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from enum import Enum


class ExecutionMode(Enum):
    STRICT = "strict"
    BOUNDED = "bounded"
    EXPLORATORY = "exploratory"


__all__ = ["ExecutionMode"]
