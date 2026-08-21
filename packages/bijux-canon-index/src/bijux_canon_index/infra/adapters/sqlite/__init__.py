# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Package exports for SQLite."""

from __future__ import annotations

from .backend import sqlite_backend
from .lexical import (
    LexicalChunk,
    LexicalIndexCorruptionError,
    LexicalIndexManifest,
    LexicalSearchResult,
    SQLiteLexicalIndex,
)

__all__ = [
    "LexicalChunk",
    "LexicalIndexCorruptionError",
    "LexicalIndexManifest",
    "LexicalSearchResult",
    "SQLiteLexicalIndex",
    "sqlite_backend",
]
