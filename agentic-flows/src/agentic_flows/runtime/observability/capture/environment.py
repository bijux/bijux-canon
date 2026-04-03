# SPDX-License-Identifier: Apache-2.0
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


def compute_environment_fingerprint() -> str:
    """Execute compute_environment_fingerprint and enforce its contract."""
    packages = {
        "bijux-agent": metadata.version("bijux-agent"),
        "bijux-cli": metadata.version("bijux-cli"),
        "bijux-rag": metadata.version("bijux-rag"),
        "bijux-rar": metadata.version("bijux-rar"),
        "bijux-vex": metadata.version("bijux-vex"),
    }
    snapshot = {
        "python_version": sys.version,
        "os": platform.platform(),
        "packages": packages,
    }
    return fingerprint_inputs(snapshot)
