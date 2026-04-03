# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>
"""Public API versioning and deprecation policy."""

from __future__ import annotations

PUBLIC_API_VERSION = "1.0.0"
DEPRECATION_POLICY = (
    "backward-compatible within major version; breaking changes require major bump"
)


def assert_supported_version(version: str) -> None:
    if not version.startswith(PUBLIC_API_VERSION.split(".")[0]):
        raise ValueError("Unsupported API version")


__all__ = ["PUBLIC_API_VERSION", "DEPRECATION_POLICY", "assert_supported_version"]
