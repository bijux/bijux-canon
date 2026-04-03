# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# Fingerprinted: python version, OS platform, bijux package versions.
# Ignored: hostnames, environment variables.

"""Module definitions for runtime/observability/capture/environment.py."""

from __future__ import annotations

from importlib import metadata
import platform
import sys

from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)


def _distribution_version(*names: str) -> str:
    """Resolve the first available distribution version from canonical and legacy names."""
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return "0.0.0"


def compute_environment_fingerprint() -> str:
    """Execute compute_environment_fingerprint and enforce its contract."""
    packages = {
        "bijux-cli": _distribution_version("bijux-cli"),
        "bijux-llm-agent": _distribution_version("bijux-llm-agent", "bijux-agent"),
        "bijux-llm-rag": _distribution_version("bijux-llm-rag", "bijux-rag"),
        "bijux-llm-rar": _distribution_version("bijux-llm-rar", "bijux-rar"),
        "bijux-llm-vex": _distribution_version("bijux-llm-vex", "bijux-vex"),
    }
    snapshot = {
        "python_version": sys.version,
        "os": platform.platform(),
        "packages": packages,
    }
    return fingerprint_inputs(snapshot)
