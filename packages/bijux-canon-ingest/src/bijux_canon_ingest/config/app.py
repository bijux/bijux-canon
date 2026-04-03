# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application configuration models."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_ingest.config.ingest import IngestConfig


@dataclass(frozen=True)
class AppConfig:
    input_path: str
    output_path: str
    ingest: IngestConfig


__all__ = ["AppConfig"]
