# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Application-level boundary config (end-of-Bijux RAG)."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_rag.rag.config import RagConfig


@dataclass(frozen=True)
class AppConfig:
    input_path: str
    output_path: str
    rag: RagConfig


__all__ = ["AppConfig"]
