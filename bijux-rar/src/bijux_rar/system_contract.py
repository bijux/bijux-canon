# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""System contract enforcement hooks."""

from __future__ import annotations

from bijux_rar.core.invariants import (
    SUPPORTED_CANONICALIZATION_VERSIONS,
    SUPPORTED_FINGERPRINT_ALGOS,
    SUPPORTED_RUNTIME_PROTOCOL_VERSIONS,
    SUPPORTED_TRACE_SCHEMA_VERSIONS,
)

INVARIANT_IDS = {
    "INV-DET-001",
    "INV-GRD-001",
    "INV-GRD-002",
    "INV-ART-001",
    "INV-SCH-001",
    "INV-ORD-001",
    "INV-LNK-001",
    "INV-EVD-001",
}


def assert_system_contract() -> None:
    """Fail fast if core system contract is violated."""
    if {1, 2} != SUPPORTED_TRACE_SCHEMA_VERSIONS:
        raise RuntimeError("INV-SCH-001 violated: unsupported trace schema set changed")
    if {1} != SUPPORTED_RUNTIME_PROTOCOL_VERSIONS:
        raise RuntimeError("INV-SCH-001 violated: runtime protocol versions changed")
    if {1} != SUPPORTED_CANONICALIZATION_VERSIONS:
        raise RuntimeError("INV-DET-001 violated: canonicalization versions changed")
    if {"sha256"} != SUPPORTED_FINGERPRINT_ALGOS:
        raise RuntimeError("INV-DET-001 violated: fingerprint algos changed")
