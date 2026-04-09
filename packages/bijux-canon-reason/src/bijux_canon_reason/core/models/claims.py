# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Claims helpers for core logic."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
import re
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.models.base import JsonValue, StableModel


class SupportKind(StrEnum):
    """Enumeration of support kind."""

    claim = "claim"
    evidence = "evidence"
    tool_call = "tool_call"


class SupportRef(StableModel):
    """Immutable support reference with mandatory span and hash."""

    kind: SupportKind
    ref_id: str
    span: tuple[int, int]
    snippet_sha256: str
    hash_algo: Literal["sha256"] = "sha256"

    model_config = ConfigDict(frozen=True)

    @field_validator("span")
    @classmethod
    def _validate_span(cls, value: tuple[int, int]) -> tuple[int, int]:
        """Validate span."""
        start, end = int(value[0]), int(value[1])
        if start < 0 or end <= start:
            raise ValueError("span must satisfy 0 <= start < end")
        return (start, end)

    @field_validator("snippet_sha256")
    @classmethod
    def _validate_snippet_sha(cls, value: str) -> str:
        """Validate snippet sha."""
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("snippet_sha256 must be 64 lowercase hex characters")
        return value


class ClaimStatus(StrEnum):
    """Enumeration of claim status."""

    proposed = "proposed"
    validated = "validated"
    rejected = "rejected"


class ClaimType(StrEnum):
    """Enumeration of claim type."""

    derived = "derived"
    observed = "observed"
    assumed = "assumed"


class Claim(StableModel):
    """Represents claim."""

    id: str = ""
    statement: str
    status: ClaimStatus = ClaimStatus.proposed
    confidence: float = 0.0
    supports: list[SupportRef] = Field(default_factory=list)
    claim_type: ClaimType = ClaimType.derived
    structured: dict[str, JsonValue] | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_supports(cls, values: dict[str, object]) -> dict[str, object]:
        """Handle alias supports."""
        if (
            isinstance(values, dict)
            and "support_refs" in values
            and "supports" not in values
        ):
            values["supports"] = values.pop("support_refs")
        return values

    def with_content_id(self) -> Claim:
        """Handle with content ID."""
        cid = stable_id(
            "claim",
            {
                "statement": self.statement,
                "status": self.status,
                "confidence": self.confidence,
                "supports": [
                    support.model_dump(mode="json") for support in self.supports
                ],
                "claim_type": self.claim_type,
                "structured": self.structured,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> Claim:
        """Ensure ID."""
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "claim",
                    {
                        "statement": self.statement,
                        "status": self.status,
                        "confidence": self.confidence,
                        "supports": [
                            support.model_dump(mode="json") for support in self.supports
                        ],
                        "claim_type": self.claim_type,
                        "structured": self.structured,
                    },
                ),
            )
        return self

    @property
    def support_refs(self) -> list[SupportRef]:
        """Handle support refs."""
        return self.supports

    @property
    def content(self) -> dict[str, JsonValue]:
        """Handle content."""
        return {"statement": self.statement}


class EvidenceRef(StableModel):
    """Represents evidence ref."""

    id: str = ""
    uri: str
    sha256: str
    span: tuple[int, int]
    chunk_id: str
    content_path: str = ""

    @field_validator("span")
    @classmethod
    def _validate_span(cls, value: tuple[int, int]) -> tuple[int, int]:
        """Validate span."""
        start, end = int(value[0]), int(value[1])
        if start < 0 or end <= start:
            raise ValueError("span must satisfy 0 <= start < end")
        return (start, end)

    @field_validator("chunk_id")
    @classmethod
    def _validate_chunk_id(cls, value: str) -> str:
        """Validate chunk ID."""
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("chunk_id must be 64 lowercase hex characters")
        return value

    @field_validator("content_path")
    @classmethod
    def _safe_content_path(cls, value: str) -> str:
        """Reject hostile paths from untrusted trace inputs."""
        if value == "":
            return value
        if "\\" in value:
            raise ValueError("content_path must use POSIX separators ('/')")
        if value.startswith("/"):
            raise ValueError("content_path must be relative")
        if re.match(r"^[A-Za-z]:", value):
            raise ValueError("content_path must not include a drive prefix")
        path = PurePosixPath(value)
        if any(part == ".." for part in path.parts):
            raise ValueError("content_path must not contain '..'")
        if any(part == "" for part in path.parts):
            raise ValueError("content_path must not contain empty segments")
        return str(path)

    def with_content_id(self) -> EvidenceRef:
        """Handle with content ID."""
        cid = stable_id(
            "evidence",
            {
                "uri": self.uri,
                "sha256": self.sha256,
                "span": self.span,
                "chunk_id": self.chunk_id,
                "content_path": self.content_path,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> EvidenceRef:
        """Ensure ID."""
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "evidence",
                    {
                        "uri": self.uri,
                        "sha256": self.sha256,
                        "span": self.span,
                        "chunk_id": self.chunk_id,
                        "content_path": self.content_path,
                    },
                ),
            )
        return self


__all__ = [
    "Claim",
    "ClaimStatus",
    "ClaimType",
    "EvidenceRef",
    "SupportKind",
    "SupportRef",
]
