# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginContract:
    determinism: str
    randomness_sources: tuple[str, ...]
    approximation: bool


__all__ = ["PluginContract"]
