# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Reusable option declarations for CLI command modules."""

from __future__ import annotations

import typer

ND_WARMUP_OPTION = typer.Option(
    None, "--nd-warmup-queries", help="Path to JSON warmup query vectors"
)
ND_TUNE_CACHE_OPTION = typer.Option(
    None, "--cache", help="Optional path to cache tuning results"
)
ND_TUNE_DATASET_DIR_OPTION = typer.Option(
    None, "--dataset-dir", help="Path to dataset directory for tuning"
)

__all__ = [
    "ND_TUNE_CACHE_OPTION",
    "ND_TUNE_DATASET_DIR_OPTION",
    "ND_WARMUP_OPTION",
]
