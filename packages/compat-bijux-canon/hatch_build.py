"""Hatch metadata hook that pins the canonical package to the compat version."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """Populate wheel dependencies using the package version resolved by Hatch."""

    def update(self, metadata: MutableMapping[str, Any]) -> None:
        """Attach the canonical compatibility dependency at the same version."""
        canonical_name = self.config["canonical-name"]
        version = metadata.get("version")
        if not version:
            raise RuntimeError("Compatibility package version is not available")
        metadata["dependencies"] = [f"{canonical_name}=={version}"]
