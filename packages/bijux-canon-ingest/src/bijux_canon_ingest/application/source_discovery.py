# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application entrypoint for deterministic source-directory discovery."""

from __future__ import annotations

from bijux_canon_ingest.domain.source_discovery import DiscoveryPolicy, DiscoveryResult
from bijux_canon_ingest.infra.adapters.directory_source import (
    discover_directory_sources,
)


def discover_sources(policy: DiscoveryPolicy) -> DiscoveryResult:
    """Discover immutable source identities under the supplied policy."""

    return discover_directory_sources(policy)


__all__ = ["discover_sources"]
