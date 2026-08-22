# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Support models for optional distributed pipeline compilers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib


@dataclass(frozen=True, slots=True)
class DistributedCompilerSupport:
    backend: str
    available: bool
    implemented: bool
    reason: str | None = None


class DistributedCompilerError(RuntimeError):
    def __init__(self, *, support: DistributedCompilerSupport) -> None:
        self.support = support
        message = support.reason or f"{support.backend} compiler is not available"
        super().__init__(message)


def detect_support(
    *,
    backend: str,
    modules: tuple[str, ...],
    implemented: bool,
    implementation_reason: str,
) -> DistributedCompilerSupport:
    try:
        for module_name in modules:
            importlib.import_module(module_name)
    except Exception as exc:
        return DistributedCompilerSupport(
            backend=backend,
            available=False,
            implemented=implemented,
            reason=str(exc),
        )

    if not implemented:
        return DistributedCompilerSupport(
            backend=backend,
            available=False,
            implemented=False,
            reason=implementation_reason,
        )

    return DistributedCompilerSupport(
        backend=backend,
        available=True,
        implemented=True,
        reason=None,
    )


__all__ = [
    "DistributedCompilerSupport",
    "DistributedCompilerError",
    "detect_support",
]
