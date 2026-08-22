# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Hash-chained mappings from normalized text to immutable source bytes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal, get_args

from bijux_canon_ingest.domain.document_extraction import SourceLocator

TransformationOperation = Literal[
    "unicode_normalize",
    "case_fold",
    "whitespace_normalize",
    "trim",
    "segment",
]

_OPERATIONS = frozenset(get_args(TransformationOperation))


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


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True, slots=True)
class SourceByteSpan:
    """An exact half-open span within one immutable source payload."""

    start: int
    end: int
    selected_bytes_sha256: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("source byte span must be non-empty and ordered")
        if not _is_sha256(self.selected_bytes_sha256):
            raise ValueError("source byte span requires a lowercase SHA-256 digest")

    def resolve(self, content: bytes) -> bytes:
        """Resolve this span and reject stale or truncated source bytes."""

        if self.end > len(content):
            raise ValueError("source byte span exceeds the supplied payload")
        selected = content[self.start : self.end]
        if hashlib.sha256(selected).hexdigest() != self.selected_bytes_sha256:
            raise ValueError(
                "source byte span hash does not match the supplied payload"
            )
        return selected

    def manifest(self) -> dict[str, object]:
        return {
            "coordinate_system": "byte",
            "end": self.end,
            "selected_bytes_sha256": self.selected_bytes_sha256,
            "start": self.start,
        }


@dataclass(frozen=True, slots=True)
class TextTransformation:
    """One deterministic, hash-verifiable text transformation."""

    operation: TransformationOperation
    implementation: str
    implementation_version: str
    configuration_sha256: str
    input_content_sha256: str
    output_content_sha256: str

    def __post_init__(self) -> None:
        if self.operation not in _OPERATIONS:
            raise ValueError("unsupported text transformation operation")
        if not self.implementation or not self.implementation_version:
            raise ValueError("text transformation implementation must be identified")
        for name in (
            "configuration_sha256",
            "input_content_sha256",
            "output_content_sha256",
        ):
            if not _is_sha256(getattr(self, name)):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")

    def manifest(self) -> dict[str, str]:
        return {
            "configuration_sha256": self.configuration_sha256,
            "implementation": self.implementation,
            "implementation_version": self.implementation_version,
            "input_content_sha256": self.input_content_sha256,
            "operation": self.operation,
            "output_content_sha256": self.output_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class NormalizedSpanMapping:
    """A normalized block or chunk with byte, human, and transformation lineage."""

    source_content_sha256: str
    source_span: SourceByteSpan
    locator: SourceLocator
    normalized_text: str
    original_text_sha256: str
    normalized_start: int
    normalized_end: int
    transformations: tuple[TextTransformation, ...]
    parent_mapping_sha256: str | None = None

    def __post_init__(self) -> None:
        if not _is_sha256(self.source_content_sha256):
            raise ValueError("span mapping requires a lowercase source SHA-256 digest")
        if not self.normalized_text:
            raise ValueError("span mapping normalized text must not be empty")
        if self.normalized_start < 0 or self.normalized_end <= self.normalized_start:
            raise ValueError("normalized character span must be non-empty and ordered")
        if self.normalized_end - self.normalized_start != len(self.normalized_text):
            raise ValueError("normalized character span length must match its text")
        if not _is_sha256(self.original_text_sha256):
            raise ValueError("span mapping requires an original text SHA-256 digest")
        if (
            self.parent_mapping_sha256 is not None
            and not self.parent_mapping_sha256.startswith("sha256:")
        ):
            raise ValueError("parent mapping identity must use sha256:<digest>")
        if not self.transformations:
            raise ValueError("span mapping requires at least one transformation")
        for previous, current in zip(
            self.transformations, self.transformations[1:], strict=False
        ):
            if previous.output_content_sha256 != current.input_content_sha256:
                raise ValueError("span mapping transformation hashes must form a chain")
        if (
            self.transformations[0].input_content_sha256
            != self.source_span.selected_bytes_sha256
        ):
            raise ValueError(
                "span mapping chain must begin at its selected source bytes"
            )
        if (
            self.transformations[-1].output_content_sha256
            != self.normalized_text_sha256
        ):
            raise ValueError("span mapping chain must end at its normalized text")

    @property
    def normalized_text_sha256(self) -> str:
        return _text_sha256(self.normalized_text)

    @property
    def mapping_sha256(self) -> str:
        payload = self._payload()
        return _identity(payload)

    def resolve_source_bytes(self, content: bytes) -> bytes:
        """Resolve the immutable source span after validating whole-source identity."""

        if hashlib.sha256(content).hexdigest() != self.source_content_sha256:
            raise ValueError(
                "source payload does not match the mapping source identity"
            )
        return self.source_span.resolve(content)

    def _payload(self) -> dict[str, object]:
        return {
            "locator": self.locator.manifest(),
            "normalized_character_span": {
                "coordinate_system": "unicode_code_point",
                "end": self.normalized_end,
                "start": self.normalized_start,
            },
            "normalized_text": self.normalized_text,
            "normalized_text_sha256": self.normalized_text_sha256,
            "original_text_sha256": self.original_text_sha256,
            "parent_mapping_sha256": self.parent_mapping_sha256,
            "schema_version": "bijux.canon.ingest.normalized_span_mapping.v1",
            "source_content_sha256": self.source_content_sha256,
            "source_span": self.source_span.manifest(),
            "transformations": [item.manifest() for item in self.transformations],
        }

    def manifest(self) -> dict[str, object]:
        """Return the complete source-resolving mapping and its identity."""

        payload = self._payload()
        return {"mapping_sha256": _identity(payload), **payload}


__all__ = [
    "NormalizedSpanMapping",
    "SourceByteSpan",
    "TextTransformation",
    "TransformationOperation",
]
