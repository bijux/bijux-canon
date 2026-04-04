# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Argparse construction for pipeline-mode CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_pipeline_parser() -> argparse.ArgumentParser:
    """Build the stable argparse parser for pipeline-mode commands."""

    parser = argparse.ArgumentParser(prog="bijux-canon-ingest")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        help="Override a.b.c=value",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output JSONL path for chunks",
    )
    return parser


__all__ = ["build_pipeline_parser"]
