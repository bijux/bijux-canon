# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""
Versioned API surface for bijux-canon-index.

This module is the only supported import path for the public FastAPI app in v1.
"""

from __future__ import annotations

from bijux_vex.boundaries.api.app import build_app

__all__ = ["build_app"]
