# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Persist complete inspectable RAG executions as immutable JSON objects."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.fingerprints import canonical_dumps
from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)

_SENSITIVE_KEYS = frozenset(
    {"access_token", "api_key", "authorization", "credential", "password", "secret"}
)


class RagExecutionMode(StrEnum):
    """Synthesis path represented by an execution manifest."""

    credential_free = "credential_free"
    structured_provider = "structured_provider"


class RagExecutionStageKind(StrEnum):
    """Required and optional inspectable RAG execution stages."""

    prompt_template = "prompt_template"
    evidence_packet = "evidence_packet"
    synthesis_output = "synthesis_output"
    normalized_claims = "normalized_claims"
    citation_links = "citation_links"
    verification_report = "verification_report"
    admission_decision = "admission_decision"
    context_representation = "context_representation"
    budget = "budget"
    failure = "failure"
    final_answer = "final_answer"


class RagExecutionPersistenceErrorCode(StrEnum):
    """Stable persistence and secret-safety failures."""

    required_stage_missing = "required_stage_missing"
    duplicate_stage = "duplicate_stage"
    sensitive_payload = "sensitive_payload"
    known_secret_present = "known_secret_present"
    object_collision = "object_collision"
    object_missing = "object_missing"
    object_corrupt = "object_corrupt"


class RagExecutionPersistenceError(ValueError):
    """An execution cannot be safely recorded or replayed."""

    def __init__(self, code: RagExecutionPersistenceErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class RagExecutionStage(StableModel):
    """One canonical JSON stage payload and its immutable identities."""

    artifact_id: str
    kind: RagExecutionStageKind
    domain_artifact_id: str | None
    payload_sha256: str
    payload_bytes: int
    payload_json: str

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("domain_artifact_id")
    @classmethod
    def _validate_domain_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("payload_sha256")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        return require_sha256(value)

    @model_validator(mode="after")
    def _validate_stage(self) -> Self:
        encoded = self.payload_json.encode()
        if self.payload_bytes != len(encoded) or self.payload_bytes <= 0:
            raise ValueError("RAG stage payload byte count does not match")
        if hashlib.sha256(encoded).hexdigest() != self.payload_sha256:
            raise ValueError("RAG stage payload digest does not match")
        try:
            value = json.loads(self.payload_json)
        except json.JSONDecodeError as exc:
            raise ValueError("RAG stage payload is not JSON") from exc
        if canonical_dumps(value) != self.payload_json:
            raise ValueError("RAG stage payload must use canonical JSON")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("RAG stage identity does not match")
        return self


class RagExecutionBudget(StableModel):
    """Declared and observed bounded resources for one RAG execution."""

    artifact_id: str
    evidence_token_limit: int
    evidence_tokens_observed: int
    citation_limit: int
    citations_observed: int
    provider_attempt_limit: int
    provider_attempts_observed: int
    provider_input_tokens: int | None
    provider_output_tokens: int | None

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_budget(self) -> Self:
        pairs = (
            (self.evidence_token_limit, self.evidence_tokens_observed),
            (self.citation_limit, self.citations_observed),
            (self.provider_attempt_limit, self.provider_attempts_observed),
        )
        if any(
            limit <= 0 or observed < 0 or observed > limit for limit, observed in pairs
        ):
            raise ValueError("RAG observed resources exceed their declared budget")
        if any(
            value is not None and value < 0
            for value in (self.provider_input_tokens, self.provider_output_tokens)
        ):
            raise ValueError("provider token observations must not be negative")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("RAG budget identity does not match")
        return self


class RagExecutionFailure(StableModel):
    """Secret-safe inspectable failure with hashed diagnostic text."""

    artifact_id: str
    stage: RagExecutionStageKind
    code: str
    message_sha256: str

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("message_sha256")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("RAG failure code must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("RAG failure identity does not match")
        return self


class RagExecutionManifest(StableModel):
    """Complete content-addressed execution index with secret-safe hashes."""

    schema_version: str = "bijux.canon.reason.rag_execution_manifest.v1"
    artifact_id: str
    mode: RagExecutionMode
    question_sha256: str
    stage_artifact_ids: tuple[str, ...]
    budget_artifact_id: str
    failure_artifact_ids: tuple[str, ...]
    final_answer_sha256: str
    final_answer: str
    secret_redaction_count: int

    @field_validator("artifact_id", "budget_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("stage_artifact_ids", "failure_artifact_ids")
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("RAG execution identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("question_sha256", "final_answer_sha256")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        return require_sha256(value)

    @model_validator(mode="after")
    def _validate_manifest(self) -> Self:
        if not self.final_answer.strip():
            raise ValueError("RAG execution final answer must not be empty")
        if hashlib.sha256(self.final_answer.encode()).hexdigest() != (
            self.final_answer_sha256
        ):
            raise ValueError("RAG final answer digest does not match")
        if self.secret_redaction_count < 0:
            raise ValueError("secret redaction count must not be negative")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("RAG execution manifest identity does not match")
        return self


class RagExecutionBundle(StableModel):
    """Manifest and every immutable object needed for inspection and replay."""

    manifest: RagExecutionManifest
    stages: tuple[RagExecutionStage, ...]
    budget: RagExecutionBudget
    failures: tuple[RagExecutionFailure, ...]

    @model_validator(mode="after")
    def _validate_bundle(self) -> Self:
        if self.manifest.stage_artifact_ids != tuple(
            stage.artifact_id for stage in self.stages
        ):
            raise ValueError("RAG manifest stage index does not match its objects")
        if self.manifest.budget_artifact_id != self.budget.artifact_id:
            raise ValueError("RAG manifest budget identity does not match")
        if self.manifest.failure_artifact_ids != tuple(
            failure.artifact_id for failure in self.failures
        ):
            raise ValueError("RAG manifest failure index does not match")
        return self


class RagExecutionRecorder:
    """Build complete secret-safe immutable execution bundles."""

    def record(
        self,
        *,
        mode: RagExecutionMode,
        question: str,
        stage_payloads: tuple[tuple[RagExecutionStageKind, str | None, object], ...],
        budget: RagExecutionBudget,
        failures: tuple[RagExecutionFailure, ...],
        final_answer: str,
        known_secrets: tuple[str, ...] = (),
    ) -> RagExecutionBundle:
        """Validate completeness and secret safety, then create a bundle."""

        if not question.strip() or not final_answer.strip():
            raise ValueError("RAG question and final answer must not be empty")
        secret_values = tuple(secret for secret in known_secrets if secret)
        stages = tuple(
            _stage(kind, domain_id, payload)
            for kind, domain_id, payload in stage_payloads
        )
        kinds = tuple(stage.kind for stage in stages)
        if len(kinds) != len(set(kinds)):
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.duplicate_stage,
                "RAG execution contains duplicate stage kinds",
            )
        required = {
            RagExecutionStageKind.prompt_template,
            RagExecutionStageKind.evidence_packet,
            RagExecutionStageKind.synthesis_output,
            RagExecutionStageKind.normalized_claims,
            RagExecutionStageKind.citation_links,
            RagExecutionStageKind.verification_report,
            RagExecutionStageKind.admission_decision,
            RagExecutionStageKind.context_representation,
        }
        missing = required.difference(kinds)
        if missing:
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.required_stage_missing,
                "RAG execution is missing required inspectable stages",
            )
        values_to_scan = [
            question,
            final_answer,
            *(stage.payload_json for stage in stages),
        ]
        if any(secret in value for secret in secret_values for value in values_to_scan):
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.known_secret_present,
                "known credential material reached a RAG execution payload",
            )
        for stage in stages:
            if _contains_sensitive_key(json.loads(stage.payload_json)):
                raise RagExecutionPersistenceError(
                    RagExecutionPersistenceErrorCode.sensitive_payload,
                    "sensitive key reached a RAG execution payload",
                )
        answer_stage = _stage(
            RagExecutionStageKind.final_answer,
            None,
            {
                "final_answer": final_answer,
                "final_answer_sha256": hashlib.sha256(
                    final_answer.encode()
                ).hexdigest(),
            },
        )
        budget_stage = _stage(
            RagExecutionStageKind.budget,
            budget.artifact_id,
            budget.model_dump(mode="json"),
        )
        failure_stages = tuple(
            _stage(
                RagExecutionStageKind.failure,
                failure.artifact_id,
                failure.model_dump(mode="json"),
            )
            for failure in failures
        )
        all_stages = (*stages, budget_stage, *failure_stages, answer_stage)
        payload = {
            "schema_version": "bijux.canon.reason.rag_execution_manifest.v1",
            "mode": mode.value,
            "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
            "stage_artifact_ids": tuple(stage.artifact_id for stage in all_stages),
            "budget_artifact_id": budget.artifact_id,
            "failure_artifact_ids": tuple(item.artifact_id for item in failures),
            "final_answer_sha256": hashlib.sha256(final_answer.encode()).hexdigest(),
            "final_answer": final_answer,
            "secret_redaction_count": len(secret_values),
        }
        manifest = RagExecutionManifest(
            artifact_id=content_artifact_id(payload),
            mode=mode,
            question_sha256=hashlib.sha256(question.encode()).hexdigest(),
            stage_artifact_ids=tuple(stage.artifact_id for stage in all_stages),
            budget_artifact_id=budget.artifact_id,
            failure_artifact_ids=tuple(item.artifact_id for item in failures),
            final_answer_sha256=hashlib.sha256(final_answer.encode()).hexdigest(),
            final_answer=final_answer,
            secret_redaction_count=len(secret_values),
        )
        return RagExecutionBundle(
            manifest=manifest,
            stages=all_stages,
            budget=budget,
            failures=failures,
        )


class ContentAddressedRagExecutionStore:
    """Filesystem-backed immutable store rooted at an explicit caller path."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def persist(self, bundle: RagExecutionBundle) -> Path:
        """Atomically persist all objects and return the manifest path."""

        objects = self._root / "objects"
        manifests = self._root / "manifests"
        objects.mkdir(parents=True, exist_ok=True)
        manifests.mkdir(parents=True, exist_ok=True)
        for stage in bundle.stages:
            _write_immutable(
                objects / _object_name(stage.artifact_id), stage.model_dump_json()
            )
        _write_immutable(
            objects / _object_name(bundle.budget.artifact_id),
            bundle.budget.model_dump_json(),
        )
        for failure in bundle.failures:
            _write_immutable(
                objects / _object_name(failure.artifact_id), failure.model_dump_json()
            )
        manifest_path = manifests / _object_name(bundle.manifest.artifact_id)
        _write_immutable(manifest_path, bundle.model_dump_json())
        return manifest_path

    def load(self, manifest_artifact_id: str) -> RagExecutionBundle:
        """Load and validate one complete persisted execution bundle."""

        require_artifact_id(manifest_artifact_id)
        path = self._root / "manifests" / _object_name(manifest_artifact_id)
        if not path.is_file():
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.object_missing,
                "RAG execution manifest is missing",
            )
        try:
            bundle = RagExecutionBundle.model_validate_json(path.read_text())
        except (ValueError, OSError) as exc:
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.object_corrupt,
                "RAG execution manifest is corrupt",
            ) from exc
        if bundle.manifest.artifact_id != manifest_artifact_id:
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.object_corrupt,
                "RAG execution manifest identity does not match its path",
            )
        for stage in bundle.stages:
            object_path = self._root / "objects" / _object_name(stage.artifact_id)
            if (
                not object_path.is_file()
                or object_path.read_text() != stage.model_dump_json()
            ):
                raise RagExecutionPersistenceError(
                    RagExecutionPersistenceErrorCode.object_corrupt,
                    "RAG execution stage object is missing or corrupt",
                )
        indexed_objects = (
            (bundle.budget.artifact_id, bundle.budget.model_dump_json()),
            *(
                (failure.artifact_id, failure.model_dump_json())
                for failure in bundle.failures
            ),
        )
        for artifact_id, payload_json in indexed_objects:
            object_path = self._root / "objects" / _object_name(artifact_id)
            if not object_path.is_file() or object_path.read_text() != payload_json:
                raise RagExecutionPersistenceError(
                    RagExecutionPersistenceErrorCode.object_corrupt,
                    "RAG execution indexed object is missing or corrupt",
                )
        return bundle


def create_rag_execution_budget(
    *,
    evidence_token_limit: int,
    evidence_tokens_observed: int,
    citation_limit: int,
    citations_observed: int,
    provider_attempt_limit: int,
    provider_attempts_observed: int,
    provider_input_tokens: int | None,
    provider_output_tokens: int | None,
) -> RagExecutionBudget:
    """Create a content-addressed execution budget from explicit observations."""

    payload = {
        "evidence_token_limit": evidence_token_limit,
        "evidence_tokens_observed": evidence_tokens_observed,
        "citation_limit": citation_limit,
        "citations_observed": citations_observed,
        "provider_attempt_limit": provider_attempt_limit,
        "provider_attempts_observed": provider_attempts_observed,
        "provider_input_tokens": provider_input_tokens,
        "provider_output_tokens": provider_output_tokens,
    }
    return RagExecutionBudget(
        artifact_id=content_artifact_id(payload),
        evidence_token_limit=evidence_token_limit,
        evidence_tokens_observed=evidence_tokens_observed,
        citation_limit=citation_limit,
        citations_observed=citations_observed,
        provider_attempt_limit=provider_attempt_limit,
        provider_attempts_observed=provider_attempts_observed,
        provider_input_tokens=provider_input_tokens,
        provider_output_tokens=provider_output_tokens,
    )


def create_rag_execution_failure(
    *, stage: RagExecutionStageKind, code: str, message: str
) -> RagExecutionFailure:
    """Create a failure that retains only a diagnostic digest, never raw text."""

    payload = {
        "stage": stage.value,
        "code": code,
        "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
    }
    return RagExecutionFailure(
        artifact_id=content_artifact_id(payload),
        stage=stage,
        code=code,
        message_sha256=hashlib.sha256(message.encode()).hexdigest(),
    )


def _stage(
    kind: RagExecutionStageKind, domain_artifact_id: str | None, payload: object
) -> RagExecutionStage:
    if domain_artifact_id is not None:
        require_artifact_id(domain_artifact_id)
    payload_json = canonical_dumps(payload)
    payload_sha256 = hashlib.sha256(payload_json.encode()).hexdigest()
    identity_payload = {
        "kind": kind.value,
        "domain_artifact_id": domain_artifact_id,
        "payload_sha256": payload_sha256,
        "payload_bytes": len(payload_json.encode()),
        "payload_json": payload_json,
    }
    return RagExecutionStage(
        artifact_id=content_artifact_id(identity_payload),
        kind=kind,
        domain_artifact_id=domain_artifact_id,
        payload_sha256=payload_sha256,
        payload_bytes=len(payload_json.encode()),
        payload_json=payload_json,
    )


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, dict):
        if any(str(key).casefold() in _SENSITIVE_KEYS for key in value):
            return True
        return any(_contains_sensitive_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _object_name(artifact_id: str) -> str:
    return artifact_id.removeprefix("sha256:") + ".json"


def _write_immutable(path: Path, value: str) -> None:
    encoded = value.encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise RagExecutionPersistenceError(
                RagExecutionPersistenceErrorCode.object_collision,
                "RAG object identity resolves to conflicting bytes",
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".rag-object-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != encoded:
                raise RagExecutionPersistenceError(
                    RagExecutionPersistenceErrorCode.object_collision,
                    "RAG object identity resolves to conflicting bytes",
                ) from None
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


__all__ = [
    "ContentAddressedRagExecutionStore",
    "RagExecutionBudget",
    "RagExecutionBundle",
    "RagExecutionFailure",
    "RagExecutionManifest",
    "RagExecutionMode",
    "RagExecutionPersistenceError",
    "RagExecutionPersistenceErrorCode",
    "RagExecutionRecorder",
    "RagExecutionStage",
    "RagExecutionStageKind",
    "create_rag_execution_budget",
    "create_rag_execution_failure",
]
