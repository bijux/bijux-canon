# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verified vector-execution application contracts."""

from .witnesses import (
    ExactSearchCandidate,
    ExactSearchWitness,
    build_exact_search_witness,
)

__all__ = [
    "ExactSearchCandidate",
    "ExactSearchWitness",
    "build_exact_search_witness",
]
