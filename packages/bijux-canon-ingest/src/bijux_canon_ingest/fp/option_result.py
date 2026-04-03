# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Backwards-compatible Option/Result aliases.

Historically this project exposed `bijux_canon_ingest.fp.option_result`. To keep older
imports working, re-export the Result/Ok/Err types from `bijux_canon_ingest.result.types`.
"""

from __future__ import annotations

from bijux_canon_ingest.result.types import Err, Ok, Result

__all__ = ["Err", "Ok", "Result"]
