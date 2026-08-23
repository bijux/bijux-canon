# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application boundary for deterministic source-directory discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_ingest.domain.source_discovery import (
    DiscoveryLimits,
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
    SymlinkPolicy,
)
from bijux_canon_ingest.infra.adapters.directory_source import (
    discover_directory_sources,
)


@dataclass(frozen=True, slots=True)
class SourceDiscoveryRequest:
    """Transport-neutral inputs for one directory discovery operation."""

    root_name: str
    directory: Path
    include: tuple[str, ...] = ("**/*",)
    exclude: tuple[str, ...] = ()
    symlink_policy: SymlinkPolicy = "reject"
    limits: DiscoveryLimits = DiscoveryLimits()


@dataclass(frozen=True, slots=True)
class SourceDiscoveryOutcome:
    """Transport-neutral result for one directory discovery operation."""

    complete: bool
    manifest: dict[str, object]


def discover_sources(policy: DiscoveryPolicy) -> DiscoveryResult:
    """Discover immutable source identities under the supplied policy."""

    return discover_directory_sources(policy)


def discover_source_directory(
    request: SourceDiscoveryRequest,
) -> SourceDiscoveryOutcome:
    """Discover one directory without exposing domain construction to transports."""

    result = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot(request.root_name, request.directory),),
            include=request.include,
            exclude=request.exclude,
            symlink_policy=request.symlink_policy,
            limits=request.limits,
        )
    )
    return SourceDiscoveryOutcome(
        complete=result.complete,
        manifest=result.manifest(),
    )


__all__ = [
    "SourceDiscoveryOutcome",
    "SourceDiscoveryRequest",
    "discover_source_directory",
    "discover_sources",
]
