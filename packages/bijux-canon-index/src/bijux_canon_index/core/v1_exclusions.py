# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""V1 exclusions helpers for core logic."""

from __future__ import annotations

V1_EXCLUSIONS: dict[str, str] = {
    "remote_backends": "Remote adapters are excluded in v1",
    "async_services": "Async orchestration is not part of v1",
    "streaming_search": "Streaming search is deferred beyond v1",
    "pgvector_backend": "pgvector adapter is experimental and excluded from v1 freeze",
}


def ensure_excluded(feature: str) -> None:
    """Ensure excluded."""
    if feature not in V1_EXCLUSIONS:
        raise KeyError(f"Unknown feature flag: {feature}")
    raise NotImplementedError(V1_EXCLUSIONS[feature])
