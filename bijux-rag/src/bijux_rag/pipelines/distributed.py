# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 7: optional distributed compilation scaffolding (end-of-Bijux RAG).

This module intentionally keeps hard dependencies optional. It provides a place
to host Dask/Beam compilers when those libraries are installed.
"""

from __future__ import annotations

import importlib
from typing import Any


def dask_available() -> bool:
    try:
        importlib.import_module("dask")
        importlib.import_module("dask.bag")
        return True
    except Exception:
        return False


def beam_available() -> bool:
    try:
        importlib.import_module("apache_beam")
        return True
    except Exception:
        return False


def compile_to_dask_bag(*_args: Any, **_kwargs: Any) -> Any:
    """Placeholder entrypoint for a Dask compiler (requires dask.bag installed)."""

    if not dask_available():
        raise ImportError("dask is not available")
    raise NotImplementedError("Dask compiler is optional and not enabled in this repo by default")


def compile_to_beam(*_args: Any, **_kwargs: Any) -> Any:
    """Placeholder entrypoint for an Apache Beam compiler (requires apache-beam installed)."""

    if not beam_available():
        raise ImportError("apache-beam is not available")
    raise NotImplementedError("Beam compiler is optional and not enabled in this repo by default")


__all__ = ["dask_available", "beam_available", "compile_to_dask_bag", "compile_to_beam"]
