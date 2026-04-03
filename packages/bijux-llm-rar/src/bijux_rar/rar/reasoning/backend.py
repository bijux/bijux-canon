# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bijux_rar.rar.reasoning.extractive import (
    Citation,
    Derivation,
    derive_extractive_answer,
)


class ReasonerBackend(Protocol):
    """Reasoner interface that produces structured derivations."""

    def derive(
        self,
        *,
        question: str,
        evidence: list[tuple[str, bytes]],
        max_citations: int,
    ) -> Derivation: ...


@dataclass(frozen=True)
class BaselineReasoner:
    """Deterministic extractive baseline reasoner."""

    def derive(
        self,
        *,
        question: str,
        evidence: list[tuple[str, bytes]],
        max_citations: int,
    ) -> Derivation:
        return derive_extractive_answer(
            question=question, evidence=evidence, max_citations=max_citations
        )


__all__ = ["ReasonerBackend", "BaselineReasoner", "Citation", "Derivation"]
