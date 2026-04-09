# SPDX-License-Identifier: Apache-2.0
"""Policies helpers for core logic."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

from bijux_canon_index.core.identity.ids import make_id


class IdGenerationStrategy(Protocol):
    """Represents ID generation strategy."""
    def next_artifact_id(self) -> str:
        """Return the next artifact ID."""

        ...

    def document_id(self, text: str) -> str:
        """Return the document ID for a text payload."""

        ...

    def chunk_id(self, document_id: str, ordinal: int) -> str:
        """Return the chunk ID for a document segment."""

        ...

    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str:
        """Return the vector ID for an embedding payload."""

        ...


@dataclass(frozen=True)
class EnvArtifactIdPolicy(IdGenerationStrategy):
    """Represents env artifact ID policy."""
    default_artifact_id: str = "art-1"
    env_var: str = "BIJUX_CANON_INDEX_ARTIFACT_ID"

    def next_artifact_id(self) -> str:
        """Handle next artifact ID."""
        return os.getenv(self.env_var, self.default_artifact_id)

    def document_id(self, text: str) -> str:
        """Handle document ID."""
        return make_id("doc", (self.default_artifact_id, text))

    def chunk_id(self, document_id: str, ordinal: int) -> str:
        """Handle chunk ID."""
        return make_id("chk", (document_id, ordinal))

    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str:
        """Handle vector ID."""
        return make_id("vec", (chunk_id, values))


@dataclass(frozen=True)
class ContentAddressedIdPolicy(IdGenerationStrategy):
    """Represents content addressed ID policy."""
    salt: str = "bijux-canon-index"

    def next_artifact_id(self) -> str:
        """Handle next artifact ID."""
        return EnvArtifactIdPolicy().next_artifact_id()

    def document_id(self, text: str) -> str:
        """Handle document ID."""
        return make_id("doc", (self.salt, text))

    def chunk_id(self, document_id: str, ordinal: int) -> str:
        """Handle chunk ID."""
        return make_id("chk", (self.salt, document_id, ordinal))

    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str:
        """Handle vector ID."""
        return make_id("vec", (self.salt, chunk_id, values))


@dataclass(frozen=True)
class FingerprintPolicy:
    """Represents fingerprint policy."""
    prefix: str = "exec"

    def execution_id(self, payload: object) -> str:
        """Handle execution ID."""
        return make_id(self.prefix, payload)


__all__ = [
    "IdGenerationStrategy",
    "EnvArtifactIdPolicy",
    "ContentAddressedIdPolicy",
    "FingerprintPolicy",
]
