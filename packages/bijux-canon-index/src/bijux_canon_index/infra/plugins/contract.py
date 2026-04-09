# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Contract helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginContract:
    """Represents plugin contract."""

    determinism: str
    randomness_sources: tuple[str, ...]
    approximation: bool


__all__ = ["PluginContract"]
