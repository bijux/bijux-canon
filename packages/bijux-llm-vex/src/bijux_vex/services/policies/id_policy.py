# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

from bijux_vex.core.identity.ids import make_id


class IdGenerationStrategy(Protocol):
    def next_artifact_id(self) -> str: ...
    def document_id(self, text: str) -> str: ...
    def chunk_id(self, document_id: str, ordinal: int) -> str: ...
    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str: ...


@dataclass(frozen=True)
class EnvArtifactIdPolicy(IdGenerationStrategy):
    default_artifact_id: str = "art-1"
    env_var: str = "BIJUX_VEX_ARTIFACT_ID"

    def next_artifact_id(self) -> str:
        return os.getenv(self.env_var, self.default_artifact_id)

    def document_id(self, text: str) -> str:
        return make_id("doc", (self.default_artifact_id, text))

    def chunk_id(self, document_id: str, ordinal: int) -> str:
        return make_id("chk", (document_id, ordinal))

    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str:
        return make_id("vec", (chunk_id, values))


@dataclass(frozen=True)
class ContentAddressedIdPolicy(IdGenerationStrategy):
    salt: str = "bijux-vex"

    def next_artifact_id(self) -> str:
        return EnvArtifactIdPolicy().next_artifact_id()

    def document_id(self, text: str) -> str:
        return make_id("doc", (self.salt, text))

    def chunk_id(self, document_id: str, ordinal: int) -> str:
        return make_id("chk", (self.salt, document_id, ordinal))

    def vector_id(self, chunk_id: str, values: tuple[float, ...]) -> str:
        return make_id("vec", (self.salt, chunk_id, values))


@dataclass(frozen=True)
class FingerprintPolicy:
    prefix: str = "exec"

    def execution_id(self, payload: object) -> str:
        return make_id(self.prefix, payload)


__all__ = [
    "IdGenerationStrategy",
    "EnvArtifactIdPolicy",
    "ContentAddressedIdPolicy",
    "FingerprintPolicy",
]
