# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed immutable inputs and outcomes for Runtime run publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from bijux_canon_runtime.ontology.ids import ArtifactID

_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class RuntimeRunPublicationError(RuntimeError):
    """A run cannot be published as a complete immutable receipt."""


class ReplayPublicationDisposition(StrEnum):
    """Replay conclusion bound into a run publication receipt."""

    NOT_REQUESTED = "not_requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ReplayPublicationStatus:
    """Exact replay lineage and comparison result for publication."""

    disposition: ReplayPublicationDisposition
    source_attempt_id: str | None = None
    replay_attempt_id: str | None = None
    comparison_sha256: str | None = None

    def __post_init__(self) -> None:
        values = (
            self.source_attempt_id,
            self.replay_attempt_id,
            self.comparison_sha256,
        )
        if self.disposition is ReplayPublicationDisposition.NOT_REQUESTED:
            if any(value is not None for value in values):
                raise ValueError("unrequested replay cannot contain replay lineage")
            return
        if any(value is None or not value.strip() for value in values):
            raise ValueError("replay publication requires complete immutable lineage")
        assert self.comparison_sha256 is not None
        if _DIGEST.fullmatch(self.comparison_sha256) is None:
            raise ValueError("replay comparison identity must be a SHA-256 digest")


@dataclass(frozen=True, slots=True)
class RunPublicationBindings:
    """Immutable external identities required to reproduce a published run."""

    source_commit: str
    corpus_artifact_id: ArtifactID
    index_artifact_id: ArtifactID
    model_artifact_id: ArtifactID
    configuration_artifact_id: ArtifactID

    def __post_init__(self) -> None:
        if _COMMIT_SHA.fullmatch(self.source_commit) is None:
            raise ValueError("publication source commit must be full lowercase Git SHA")
        for value in (
            self.corpus_artifact_id,
            self.index_artifact_id,
            self.model_artifact_id,
            self.configuration_artifact_id,
        ):
            if _ARTIFACT_ID.fullmatch(str(value)) is None:
                raise ValueError("publication bindings must use artifact identities")


@dataclass(frozen=True, slots=True)
class RuntimeRunPublicationOutcome:
    """One admitted receipt and its stable content-derived citation."""

    publication_id: str
    revision: int
    receipt_artifact_id: ArtifactID
    stable_citation: str
    selected_attempt_id: str
    artifact_count: int
    check_count: int
    reused: bool


__all__ = [
    "ReplayPublicationDisposition",
    "ReplayPublicationStatus",
    "RunPublicationBindings",
    "RuntimeRunPublicationError",
    "RuntimeRunPublicationOutcome",
]
