# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Internal execution ABI fingerprinting and stability guards."""

from __future__ import annotations

from dataclasses import MISSING, fields
from typing import Any

from bijux_vex.core.execution_result import ExecutionResult
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest

EXECUTION_ABI_VERSION = "1.3.21"
EXPECTED_FINGERPRINT = (
    "02c5e96fdd875cd6732ed26c0c0eb99dd186e70e3c0e6fd1535339bad3d939c6"
)


def _field_signature(cls: type[Any]) -> tuple[tuple[str, Any, Any], ...]:
    sig = []
    for f in fields(cls):
        default = f.default if f.default is not MISSING else None
        default_factory = (
            f.default_factory
            if getattr(f, "default_factory", MISSING) is not MISSING
            else None
        )
        sig.append((f.name, default, bool(default_factory)))
    return tuple(sig)


def execution_abi_payload() -> dict[str, object]:
    return {
        "abi_version": EXECUTION_ABI_VERSION,
        "execution_request_fields": _field_signature(ExecutionRequest),
        "execution_result_fields": _field_signature(ExecutionResult),
        "execution_artifact_fields": _field_signature(ExecutionArtifact),
    }


def execution_abi_fingerprint() -> str:
    return fingerprint(execution_abi_payload())


def assert_execution_abi() -> None:
    if execution_abi_fingerprint() != EXPECTED_FINGERPRINT:
        raise RuntimeError(
            "Execution ABI drift detected; bump version and migrate artifacts"
        )


__all__ = [
    "EXECUTION_ABI_VERSION",
    "execution_abi_payload",
    "execution_abi_fingerprint",
    "assert_execution_abi",
]
