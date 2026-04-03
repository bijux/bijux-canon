# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Backwards-compatible Option/Result aliases.

Historically this project exposed `bijux_rag.fp.option_result`. To keep older
imports working, re-export the Result/Ok/Err types from `bijux_rag.result.types`.
"""

from __future__ import annotations

from bijux_rag.result.types import Err, Ok, Result

__all__ = ["Err", "Ok", "Result"]
