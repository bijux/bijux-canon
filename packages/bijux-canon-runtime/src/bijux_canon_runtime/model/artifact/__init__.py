"""Domain model definitions.

Immutable unless explicitly finalized.
No runtime side effects.
"""

from bijux_canon_runtime.model.artifact.content_address import (
    AddressedArtifact,
    ImmutableArtifactDescriptor,
    LogicalArtifactReference,
    canonical_json_bytes,
    describe_artifact,
)

__all__ = [
    "AddressedArtifact",
    "ImmutableArtifactDescriptor",
    "LogicalArtifactReference",
    "canonical_json_bytes",
    "describe_artifact",
]
