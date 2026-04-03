# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application configuration models."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_rag.config.rag import RagConfig


@dataclass(frozen=True)
class AppConfig:
    input_path: str
    output_path: str
    rag: RagConfig


__all__ = ["AppConfig"]
