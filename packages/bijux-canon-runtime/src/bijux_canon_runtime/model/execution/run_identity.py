# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stable semantic run identities and immutable execution lineage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import re

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    RetrievalFilters,
    RuntimeOutputPolicy,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID, RunID

_ARTIFACT_ID = re.compile(r"sha256:[0-9a-f]{64}")
_IDENTITY = re.compile(r"(?:run|attempt|retry|replay|publication)_v1_[0-9a-f]{64}")


def _identity(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}_v1_{digest}"


def _require_artifact_id(value: ArtifactID | None, field_name: str) -> None:
    if value is not None and _ARTIFACT_ID.fullmatch(str(value)) is None:
        raise ValueError(f"{field_name} must be an immutable artifact identity")


@dataclass(frozen=True, slots=True)
class SemanticRunInputs:
    """Resolved semantic inputs that define one run independently of execution."""

    operation: RuntimeRequestOperation
    scope: str
    query: str | None
    corpus_artifact_id: ArtifactID | None
    index_artifact_id: ArtifactID | None
    filters: RetrievalFilters
    top_k: int | None
    output_policy: RuntimeOutputPolicy | None
    execution_configuration_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.scope.strip():
            raise ValueError("semantic run scope must not be empty")
        if self.query is not None and not self.query.strip():
            raise ValueError("semantic run query must not be empty")
        _require_artifact_id(self.corpus_artifact_id, "corpus_artifact_id")
        _require_artifact_id(self.index_artifact_id, "index_artifact_id")
        if self.top_k is not None and not 1 <= self.top_k <= 1000:
            raise ValueError("semantic run top_k must be between 1 and 1000")
        if self.corpus_artifact_id is None and self.index_artifact_id is None:
            raise ValueError(
                "semantic run requires a resolved corpus or index artifact"
            )
        if self.execution_configuration_sha256 is not None and re.fullmatch(
            r"[0-9a-f]{64}", self.execution_configuration_sha256
        ) is None:
            raise ValueError("execution configuration identity must be a sha256")

    def identity_payload(self) -> dict[str, object]:
        """Return execution-independent canonical semantics for hashing."""
        operation = (
            RuntimeRequestOperation.RUN
            if self.operation is RuntimeRequestOperation.REPLAY
            else self.operation
        )
        payload: dict[str, object] = {
            "corpus_artifact_id": self.corpus_artifact_id,
            "filters": {
                "document_ids": list(self.filters.document_ids),
                "source_uris": list(self.filters.source_uris),
            },
            "index_artifact_id": self.index_artifact_id,
            "operation": operation.value,
            "output_policy": (
                None if self.output_policy is None else asdict(self.output_policy)
            ),
            "query": self.query,
            "schema_version": "bijux.runtime.semantic-run-inputs.v1",
            "scope": self.scope,
            "top_k": self.top_k,
        }
        if self.execution_configuration_sha256 is not None:
            payload["execution_configuration_sha256"] = (
                self.execution_configuration_sha256
            )
            payload["schema_version"] = "bijux.runtime.semantic-run-inputs.v2"
        return payload


@dataclass(frozen=True, slots=True)
class SemanticRunIdentity:
    """Content identity shared by equivalent live and replay executions."""

    run_id: RunID
    semantic_sha256: str
    inputs: SemanticRunInputs

    @classmethod
    def derive(cls, inputs: SemanticRunInputs) -> SemanticRunIdentity:
        """Derive an immutable run identity from resolved semantic inputs."""
        payload = inputs.identity_payload()
        semantic_sha256 = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        return cls(
            run_id=RunID(f"run_v1_{semantic_sha256}"),
            semantic_sha256=semantic_sha256,
            inputs=inputs,
        )

    def __post_init__(self) -> None:
        expected_sha256 = hashlib.sha256(
            canonical_json_bytes(self.inputs.identity_payload())
        ).hexdigest()
        if self.semantic_sha256 != expected_sha256:
            raise ValueError("semantic run hash does not match its inputs")
        if self.run_id != RunID(f"run_v1_{self.semantic_sha256}"):
            raise ValueError("semantic run identity does not match its inputs")


class AttemptRelation(StrEnum):
    """Why an immutable execution attempt follows another attempt."""

    INITIAL = "initial"
    RETRY = "retry"
    REPLAY = "replay"


@dataclass(frozen=True, slots=True)
class ExecutionAttemptIdentity:
    """One immutable process execution, distinct from semantic run identity."""

    attempt_id: str
    run_id: RunID
    request_id: RequestID
    attempt_number: int
    relation: AttemptRelation
    source_attempt_id: str | None
    supersedes_attempt_id: str | None
    retry_id: str | None
    replay_id: str | None
    process_id: str

    @classmethod
    def initial(
        cls,
        *,
        run: SemanticRunIdentity,
        request_id: RequestID,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        """Create the first execution attempt for one semantic run."""
        return cls._derive(
            run=run,
            request_id=request_id,
            attempt_number=1,
            relation=AttemptRelation.INITIAL,
            source=None,
            process_id=process_id,
        )

    @classmethod
    def retry(
        cls,
        *,
        run: SemanticRunIdentity,
        request_id: RequestID,
        source: ExecutionAttemptIdentity,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        """Create a retry that explicitly supersedes a prior attempt."""
        return cls._derive(
            run=run,
            request_id=request_id,
            attempt_number=source.attempt_number + 1,
            relation=AttemptRelation.RETRY,
            source=source,
            process_id=process_id,
        )

    @classmethod
    def replay(
        cls,
        *,
        run: SemanticRunIdentity,
        request_id: RequestID,
        source: ExecutionAttemptIdentity,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        """Create a replay linked to immutable inputs from a prior attempt."""
        return cls._derive(
            run=run,
            request_id=request_id,
            attempt_number=source.attempt_number + 1,
            relation=AttemptRelation.REPLAY,
            source=source,
            process_id=process_id,
        )

    @classmethod
    def replay_persisted(
        cls,
        *,
        request_id: RequestID,
        source: ExecutionAttemptIdentity,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        """Create a replay from a validated persisted attempt identity."""
        return cls._derive_from_run_id(
            run_id=source.run_id,
            request_id=request_id,
            attempt_number=source.attempt_number + 1,
            relation=AttemptRelation.REPLAY,
            source=source,
            process_id=process_id,
        )

    @classmethod
    def retry_persisted(
        cls,
        *,
        request_id: RequestID,
        source: ExecutionAttemptIdentity,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        """Create a recovery retry from a validated persisted attempt."""
        return cls._derive_from_run_id(
            run_id=source.run_id,
            request_id=request_id,
            attempt_number=source.attempt_number + 1,
            relation=AttemptRelation.RETRY,
            source=source,
            process_id=process_id,
        )

    @classmethod
    def _derive(
        cls,
        *,
        run: SemanticRunIdentity,
        request_id: RequestID,
        attempt_number: int,
        relation: AttemptRelation,
        source: ExecutionAttemptIdentity | None,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        return cls._derive_from_run_id(
            run_id=run.run_id,
            request_id=request_id,
            attempt_number=attempt_number,
            relation=relation,
            source=source,
            process_id=process_id,
        )

    @classmethod
    def _derive_from_run_id(
        cls,
        *,
        run_id: RunID,
        request_id: RequestID,
        attempt_number: int,
        relation: AttemptRelation,
        source: ExecutionAttemptIdentity | None,
        process_id: str,
    ) -> ExecutionAttemptIdentity:
        if not str(request_id).strip() or not process_id.strip():
            raise ValueError("attempt request and process identities are required")
        if relation is AttemptRelation.INITIAL:
            if source is not None or attempt_number != 1:
                raise ValueError("initial attempt cannot have prior lineage")
        else:
            if source is None:
                raise ValueError("retry and replay require a source attempt")
            if source.run_id != run_id:
                raise ValueError("attempt lineage must preserve semantic run identity")
            if attempt_number != source.attempt_number + 1:
                raise ValueError("attempt lineage number must be contiguous")
        source_attempt_id = None if source is None else source.attempt_id
        lineage_payload = {
            "attempt_number": attempt_number,
            "relation": relation.value,
            "request_id": str(request_id),
            "run_id": str(run_id),
            "schema_version": "bijux.runtime.execution-attempt.v1",
            "source_attempt_id": source_attempt_id,
        }
        attempt_id = _identity("attempt", lineage_payload)
        retry_id = (
            _identity("retry", lineage_payload)
            if relation is AttemptRelation.RETRY
            else None
        )
        replay_id = (
            _identity("replay", lineage_payload)
            if relation is AttemptRelation.REPLAY
            else None
        )
        return cls(
            attempt_id=attempt_id,
            run_id=run_id,
            request_id=request_id,
            attempt_number=attempt_number,
            relation=relation,
            source_attempt_id=source_attempt_id,
            supersedes_attempt_id=source_attempt_id,
            retry_id=retry_id,
            replay_id=replay_id,
            process_id=process_id,
        )

    def __post_init__(self) -> None:
        for value in (
            self.attempt_id,
            self.retry_id,
            self.replay_id,
            self.source_attempt_id,
            self.supersedes_attempt_id,
        ):
            if value is not None and _IDENTITY.fullmatch(value) is None:
                raise ValueError("execution lineage contains an invalid identity")
        if self.attempt_number < 1 or not self.process_id.strip():
            raise ValueError("execution attempt fields are invalid")
        if self.relation is AttemptRelation.INITIAL:
            if any(
                value is not None
                for value in (
                    self.source_attempt_id,
                    self.supersedes_attempt_id,
                    self.retry_id,
                    self.replay_id,
                )
            ):
                raise ValueError("initial attempt must not contain lineage")
        elif self.source_attempt_id != self.supersedes_attempt_id:
            raise ValueError("derived attempt must explicitly supersede its source")
        if (self.retry_id is not None) != (self.relation is AttemptRelation.RETRY):
            raise ValueError("retry identity does not match attempt relation")
        if (self.replay_id is not None) != (self.relation is AttemptRelation.REPLAY):
            raise ValueError("replay identity does not match attempt relation")
        lineage_payload = {
            "attempt_number": self.attempt_number,
            "relation": self.relation.value,
            "request_id": str(self.request_id),
            "run_id": str(self.run_id),
            "schema_version": "bijux.runtime.execution-attempt.v1",
            "source_attempt_id": self.source_attempt_id,
        }
        if self.attempt_id != _identity("attempt", lineage_payload):
            raise ValueError("attempt identity does not match its lineage")
        if self.retry_id is not None and self.retry_id != _identity(
            "retry", lineage_payload
        ):
            raise ValueError("retry identity does not match its lineage")
        if self.replay_id is not None and self.replay_id != _identity(
            "replay", lineage_payload
        ):
            raise ValueError("replay identity does not match its lineage")


@dataclass(frozen=True, slots=True)
class RunPublicationIdentity:
    """A publication revision selecting one immutable execution attempt."""

    publication_id: str
    run_id: RunID
    selected_attempt_id: str
    revision: int
    supersedes_publication_id: str | None

    @classmethod
    def create(
        cls,
        *,
        run: SemanticRunIdentity,
        selected_attempt: ExecutionAttemptIdentity,
        previous: RunPublicationIdentity | None = None,
    ) -> RunPublicationIdentity:
        """Create a distinct publication identity with explicit revision lineage."""
        if selected_attempt.run_id != run.run_id:
            raise ValueError("publication attempt belongs to another semantic run")
        if previous is not None and previous.run_id != run.run_id:
            raise ValueError("publication lineage belongs to another semantic run")
        revision = 1 if previous is None else previous.revision + 1
        previous_id = None if previous is None else previous.publication_id
        payload = {
            "revision": revision,
            "run_id": str(run.run_id),
            "schema_version": "bijux.runtime.run-publication.v1",
            "selected_attempt_id": selected_attempt.attempt_id,
            "supersedes_publication_id": previous_id,
        }
        return cls(
            publication_id=_identity("publication", payload),
            run_id=run.run_id,
            selected_attempt_id=selected_attempt.attempt_id,
            revision=revision,
            supersedes_publication_id=previous_id,
        )

    def __post_init__(self) -> None:
        if _IDENTITY.fullmatch(self.publication_id) is None or self.revision < 1:
            raise ValueError("publication identity or revision is invalid")
        if _IDENTITY.fullmatch(self.selected_attempt_id) is None:
            raise ValueError("publication selected attempt identity is invalid")
        if self.revision == 1 and self.supersedes_publication_id is not None:
            raise ValueError("first publication cannot supersede another publication")
        if self.revision > 1 and (
            self.supersedes_publication_id is None
            or _IDENTITY.fullmatch(self.supersedes_publication_id) is None
        ):
            raise ValueError("publication revision requires supersession lineage")
        payload = {
            "revision": self.revision,
            "run_id": str(self.run_id),
            "schema_version": "bijux.runtime.run-publication.v1",
            "selected_attempt_id": self.selected_attempt_id,
            "supersedes_publication_id": self.supersedes_publication_id,
        }
        if self.publication_id != _identity("publication", payload):
            raise ValueError("publication identity does not match its lineage")


__all__ = [
    "AttemptRelation",
    "ExecutionAttemptIdentity",
    "RunPublicationIdentity",
    "SemanticRunIdentity",
    "SemanticRunInputs",
]
