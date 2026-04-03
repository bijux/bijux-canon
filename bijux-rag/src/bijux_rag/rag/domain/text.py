# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG subsystem ADT: chunk text (end-of-Bijux RAG; domain-modeling)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkText:
    content: str


__all__ = ["ChunkText"]
