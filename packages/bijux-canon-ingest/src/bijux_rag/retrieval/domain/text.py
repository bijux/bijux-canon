# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""Bijux RAG subsystem ADT: chunk text (end-of-Bijux RAG; domain-modeling)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkText:
    content: str


__all__ = ["ChunkText"]
