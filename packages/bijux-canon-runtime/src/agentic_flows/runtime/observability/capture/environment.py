# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>
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
        "bijux-canon-agent": _distribution_version("bijux-canon-agent", "bijux-agent"),
        "bijux-canon-ingest": _distribution_version("bijux-canon-ingest", "bijux-rag"),
        "bijux-canon-reason": _distribution_version("bijux-canon-reason", "bijux-rar"),
        "bijux-canon-index": _distribution_version("bijux-canon-index", "bijux-vex"),
    }
    snapshot = {
        "python_version": sys.version,
        "os": platform.platform(),
        "packages": packages,
    }
    return fingerprint_inputs(snapshot)
