"""Hatch metadata hook that binds runtime peers to one family version."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """Publish external requirements and exact same-version Canon peers."""

    def update(self, metadata: MutableMapping[str, Any]) -> None:
        """Attach the runtime dependency graph after VCS version resolution."""
        version = metadata.get("version")
        if not version:
            raise RuntimeError("Runtime package version is not available")
        external = self.config.get("external-dependencies", [])
        peers = self.config.get("same-version-dependencies", [])
        if not isinstance(external, list) or not all(
            isinstance(value, str) and value for value in external
        ):
            raise RuntimeError("Runtime external dependencies must be strings")
        if (
            not isinstance(peers, list)
            or not peers
            or not all(isinstance(value, str) and value for value in peers)
        ):
            raise RuntimeError("Runtime same-version dependencies must be strings")
        metadata["dependencies"] = [
            *external,
            *(f"{name}=={version}" for name in peers),
        ]
