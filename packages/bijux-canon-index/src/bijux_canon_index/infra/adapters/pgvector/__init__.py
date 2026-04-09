# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Package exports for pgvector."""

from __future__ import annotations

from bijux_canon_index.infra.adapters.pgvector.backend import (
    pgvector_backend,  # noqa: F401
)

__all__ = ["pgvector_backend"]
