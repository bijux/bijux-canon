# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic semantic chunks with mapping and content lineage."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from bijux_canon_ingest.domain.source_mapping import NormalizedSpanMapping

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_identity(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


@dataclass(frozen=True, slots=True)
class SemanticChunkingPolicy:
    """Reviewable character and overlap budgets for semantic chunk formation."""

    max_characters: int = 1_200
    overlap_characters: int = 120
    block_separator: str = "\n\n"
    boundary_strategy: Literal["hard", "sentence"] = "hard"

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_characters, bool)
            or not isinstance(self.max_characters, int)
            or self.max_characters <= 0
        ):
            raise ValueError("max_characters must be a positive integer")
        if (
            isinstance(self.overlap_characters, bool)
            or not isinstance(self.overlap_characters, int)
            or self.overlap_characters < 0
            or self.overlap_characters >= self.max_characters
        ):
            raise ValueError("overlap_characters must be within the chunk budget")
        if not self.block_separator:
            raise ValueError("block_separator must not be empty")
        if self.boundary_strategy not in {"hard", "sentence"}:
            raise ValueError("boundary_strategy must be hard or sentence")

    @property
    def policy_sha256(self) -> str:
        return _identity(self.manifest())

    def manifest(self) -> dict[str, object]:
        manifest: dict[str, object] = {
            "block_separator": self.block_separator,
            "max_characters": self.max_characters,
            "overlap_characters": self.overlap_characters,
            "schema_version": "bijux.canon.ingest.semantic_chunking_policy.v1",
        }
        if self.boundary_strategy == "sentence":
            manifest.update(
                {
                    "boundary_strategy": self.boundary_strategy,
                    "schema_version": (
                        "bijux.canon.ingest.semantic_chunking_policy.v2"
                    ),
                }
            )
        return manifest


@dataclass(frozen=True, slots=True)
class SemanticChunk:
    """One bounded normalized chunk linked to every contributing source mapping."""

    source_content_sha256: str
    chunk_index: int
    normalized_text: str
    mappings: tuple[NormalizedSpanMapping, ...]
    block_roles: tuple[str, ...]
    section_paths: tuple[tuple[str, ...], ...]
    overlap_character_count: int
    chunking_policy_sha256: str
    block_separator: str

    def __post_init__(self) -> None:
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("semantic chunk requires a lowercase source SHA-256")
        if self.chunk_index < 0 or not self.normalized_text or not self.mappings:
            raise ValueError("semantic chunk requires an index, text, and mappings")
        if any(
            mapping.source_content_sha256 != self.source_content_sha256
            for mapping in self.mappings
        ):
            raise ValueError("semantic chunk mappings must share its source identity")
        if len(self.block_roles) != len(self.mappings) or len(
            self.section_paths
        ) != len(self.mappings):
            raise ValueError("semantic chunk annotations must align with mappings")
        if any(not role for role in self.block_roles):
            raise ValueError("semantic chunk block roles must not be empty")
        reconstructed = self.block_separator.join(
            mapping.normalized_text for mapping in self.mappings
        )
        if reconstructed != self.normalized_text:
            raise ValueError("semantic chunk text must reconstruct from its mappings")
        if not 0 <= self.overlap_character_count < len(self.normalized_text):
            raise ValueError("semantic chunk overlap must be within its text")
        if not _is_identity(self.chunking_policy_sha256):
            raise ValueError("semantic chunk policy identity must use sha256:<digest>")

    @property
    def normalized_text_sha256(self) -> str:
        return _text_sha256(self.normalized_text)

    @property
    def character_count(self) -> int:
        return len(self.normalized_text)

    @property
    def token_count(self) -> int:
        return len(_TOKEN.findall(self.normalized_text))

    @property
    def canonical_fingerprint(self) -> str:
        """Return a source-byte-independent semantic content fingerprint."""

        return _identity(
            {
                "block_roles": list(self.block_roles),
                "normalized_text_sha256": self.normalized_text_sha256,
                "section_paths": [list(path) for path in self.section_paths],
            }
        )

    @property
    def chunk_id(self) -> str:
        """Return a stable content and lineage identity independent of list position."""

        return _identity(
            {
                "canonical_fingerprint": self.canonical_fingerprint,
                "chunking_policy_sha256": self.chunking_policy_sha256,
                "mapping_sha256": [mapping.mapping_sha256 for mapping in self.mappings],
                "source_content_sha256": self.source_content_sha256,
            }
        )

    def manifest(self) -> dict[str, object]:
        return {
            "block_roles": list(self.block_roles),
            "canonical_fingerprint": self.canonical_fingerprint,
            "character_count": self.character_count,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "chunking_policy_sha256": self.chunking_policy_sha256,
            "mapping_sha256": [mapping.mapping_sha256 for mapping in self.mappings],
            "normalized_text": self.normalized_text,
            "normalized_text_sha256": self.normalized_text_sha256,
            "overlap_character_count": self.overlap_character_count,
            "schema_version": "bijux.canon.ingest.semantic_chunk.v1",
            "section_paths": [list(path) for path in self.section_paths],
            "source_content_sha256": self.source_content_sha256,
            "token_count": self.token_count,
        }


__all__ = ["SemanticChunk", "SemanticChunkingPolicy"]
