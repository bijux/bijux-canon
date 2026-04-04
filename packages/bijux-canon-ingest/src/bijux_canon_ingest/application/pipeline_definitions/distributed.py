# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Optional distributed compilation boundary for pipeline definitions."""

from __future__ import annotations

from typing import Any

from bijux_canon_ingest.application.pipeline_definitions.compiler_support import (
    DistributedCompilerError,
    DistributedCompilerSupport,
    detect_support,
)


def dask_support() -> DistributedCompilerSupport:
    return detect_support(
        backend="dask",
        modules=("dask", "dask.bag"),
        implemented=False,
        implementation_reason="Dask compiler is intentionally outside this package boundary",
    )


def beam_support() -> DistributedCompilerSupport:
    return detect_support(
        backend="beam",
        modules=("apache_beam",),
        implemented=False,
        implementation_reason="Beam compiler is intentionally outside this package boundary",
    )


def dask_available() -> bool:
    return dask_support().available


def beam_available() -> bool:
    return beam_support().available


def compile_to_dask_bag(*_args: Any, **_kwargs: Any) -> Any:
    """Raise a typed boundary error for the optional Dask compiler."""

    raise DistributedCompilerError(support=dask_support())


def compile_to_beam(*_args: Any, **_kwargs: Any) -> Any:
    """Raise a typed boundary error for the optional Beam compiler."""

    raise DistributedCompilerError(support=beam_support())


__all__ = [
    "DistributedCompilerError",
    "DistributedCompilerSupport",
    "beam_available",
    "beam_support",
    "compile_to_beam",
    "compile_to_dask_bag",
    "dask_available",
    "dask_support",
]
