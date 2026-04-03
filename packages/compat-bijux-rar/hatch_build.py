from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    def update(self, metadata):
        canonical_name = self.config["canonical-name"]
        version = metadata["version"]
        metadata["dependencies"] = [f"{canonical_name}=={version}"]
