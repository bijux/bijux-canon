# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Runtime package version discovery shared across planning and observability."""

from __future__ import annotations

from importlib import metadata


def distribution_version(*distribution_names: str) -> str:
    """Return the first installed version for the given distribution names."""
    for distribution_name in distribution_names:
        try:
            return metadata.version(distribution_name)
        except metadata.PackageNotFoundError:
            continue
    return "0.0.0"


def runtime_dependency_versions() -> dict[str, str]:
    """Return canonical runtime dependency versions for environment snapshots."""
    return {
        "bijux-cli": distribution_version("bijux-cli"),
        "bijux-canon-agent": distribution_version("bijux-canon-agent"),
        "bijux-canon-ingest": distribution_version("bijux-canon-ingest"),
        "bijux-canon-reason": distribution_version("bijux-canon-reason"),
        "bijux-canon-index": distribution_version("bijux-canon-index"),
    }


__all__ = ["distribution_version", "runtime_dependency_versions"]
