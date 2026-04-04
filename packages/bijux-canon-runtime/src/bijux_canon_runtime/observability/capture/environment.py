# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# Fingerprinted: python version, OS platform, bijux package versions.
# Ignored: hostnames, environment variables.

"""Module definitions for observability/capture/environment.py."""

from __future__ import annotations

import platform
import sys

from bijux_canon_runtime.core.package_versions import runtime_dependency_versions
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)


def compute_environment_fingerprint() -> str:
    """Execute compute_environment_fingerprint and enforce its contract."""
    snapshot = {
        "python_version": sys.version,
        "os": platform.platform(),
        "packages": runtime_dependency_versions(),
    }
    return fingerprint_inputs(snapshot)
