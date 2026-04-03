from __future__ import annotations

from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        canonical_name = self.config["canonical-name"]
        version = metadata.get("version")
        if not version:
            raise RuntimeError("Compatibility package version is not available")
        metadata["dependencies"] = [f"{canonical_name}=={version}"]
