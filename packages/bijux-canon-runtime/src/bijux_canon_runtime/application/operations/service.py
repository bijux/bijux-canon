# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""One versioned application service shared by library, CLI, and HTTP."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass
import re
from typing import Protocol

from bijux_canon_runtime.application.operations.codec import (
    replay_request_from_payload,
    replay_request_payload,
    runtime_request_from_payload,
    runtime_request_payload,
)
from bijux_canon_runtime.application.operations.models import (
    ApplicationOperation,
    ReplayOperationRequest,
    RuntimeApplicationCapability,
)
from bijux_canon_runtime.model.execution.request_plan import (
    RuntimeOperationRequest,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.comparison import (
    RuntimeComparisonPolicy,
    RuntimeComparisonResult,
    RuntimeComparisonService,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobHandler,
    DurableJobManager,
    DurableJobRequest,
    DurableJobSnapshot,
    JobKind,
)
from bijux_canon_runtime.runtime.inspection import (
    RuntimeRunInspection,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.pagination import PageRequest, paginate_collections


class ApplicationCapabilityError(RuntimeError):
    """A configured application composition lacks a required owner capability."""


class RuntimeOperationExecutor(Protocol):
    """Execute one reconstructed typed request for a durable worker."""

    def __call__(
        self,
        request: RuntimeOperationRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        """Return transport-neutral JSON-compatible result metadata."""
        ...


class ReplayOperationExecutor(Protocol):
    """Execute one reconstructed replay request for a durable worker."""

    def __call__(
        self,
        request: ReplayOperationRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        """Return transport-neutral JSON-compatible replay metadata."""
        ...


class ResourceInspectionExecutor(Protocol):
    """Inspect one immutable corpus or index through its owning service."""

    def __call__(self, artifact_id: ArtifactID) -> Mapping[str, object]:
        """Return transport-neutral, JSON-compatible inspection metadata."""
        ...


def _validated_artifact_id(artifact_id: ArtifactID) -> ArtifactID:
    if re.fullmatch(r"sha256:[0-9a-f]{64}", str(artifact_id)) is None:
        raise ValueError("resource inspection requires a SHA-256 artifact identity")
    return artifact_id


def build_runtime_job_handlers(
    *,
    execute: RuntimeOperationExecutor,
    replay: ReplayOperationExecutor,
) -> Mapping[JobKind, DurableJobHandler]:
    """Bind typed application executors to restart-safe durable job payloads."""

    def execute_job(
        request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        if request.kind is not JobKind.RUN:
            raise ValueError("runtime execution handler received the wrong job kind")
        return execute(runtime_request_from_payload(request.payload), is_cancelled)

    def replay_job(
        request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        if request.kind is not JobKind.REPLAY:
            raise ValueError("runtime replay handler received the wrong job kind")
        return replay(replay_request_from_payload(request.payload), is_cancelled)

    return {JobKind.RUN: execute_job, JobKind.REPLAY: replay_job}


_METHOD_OPERATIONS = {
    ApplicationOperation.CORPUS: RuntimeRequestOperation.CORPUS_PREPARE,
    ApplicationOperation.INDEX: RuntimeRequestOperation.INDEX_BUILD,
    ApplicationOperation.RETRIEVE: RuntimeRequestOperation.RETRIEVE,
    ApplicationOperation.ASK: RuntimeRequestOperation.ASK,
    ApplicationOperation.RESEARCH: RuntimeRequestOperation.RESEARCH,
    ApplicationOperation.RUN: RuntimeRequestOperation.RUN,
}


class RuntimeApplicationServicesV2:
    """Canonical application entry point independent of transport semantics."""

    capability = RuntimeApplicationCapability(
        schema_version="bijux.runtime.application-capability.v2",
        service_version="2.0",
        operations=tuple(ApplicationOperation),
        asynchronous_operations=(
            ApplicationOperation.CORPUS,
            ApplicationOperation.INDEX,
            ApplicationOperation.RETRIEVE,
            ApplicationOperation.ASK,
            ApplicationOperation.RESEARCH,
            ApplicationOperation.RUN,
            ApplicationOperation.REPLAY,
        ),
    )

    def __init__(
        self,
        *,
        jobs: DurableJobManager,
        inspector: RuntimeRunInspector,
        comparison: RuntimeComparisonService | None = None,
        corpus_inspector: ResourceInspectionExecutor | None = None,
        index_inspector: ResourceInspectionExecutor | None = None,
    ) -> None:
        self._jobs = jobs
        self._inspector = inspector
        self._comparison = comparison or RuntimeComparisonService(inspector)
        self._corpus_inspector = corpus_inspector
        self._index_inspector = index_inspector

    def corpus(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit immutable corpus preparation work."""
        return self._submit(ApplicationOperation.CORPUS, request, idempotency_key)

    def inspect_corpus(self, corpus_id: ArtifactID) -> Mapping[str, object]:
        """Inspect one immutable corpus through the configured ingest owner."""
        if self._corpus_inspector is None:
            raise ApplicationCapabilityError(
                "corpus inspection capability is not configured"
            )
        return self._corpus_inspector(_validated_artifact_id(corpus_id))

    def index(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit persistent index construction work."""
        return self._submit(ApplicationOperation.INDEX, request, idempotency_key)

    def inspect_index(self, index_id: ArtifactID) -> Mapping[str, object]:
        """Inspect one immutable index through the configured index owner."""
        if self._index_inspector is None:
            raise ApplicationCapabilityError(
                "index inspection capability is not configured"
            )
        return self._index_inspector(_validated_artifact_id(index_id))

    def inspect_index_page(
        self,
        index_id: ArtifactID,
        *,
        page: PageRequest,
    ) -> Mapping[str, object]:
        """Inspect a bounded page of immutable index segment metadata."""
        validated = _validated_artifact_id(index_id)
        inspection = self.inspect_index(validated)
        return paginate_collections(
            inspection,
            collection_fields=("segments",),
            resource_identity={"index_id": str(validated)},
            request=page,
        )

    def retrieve(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit exact evidence retrieval work."""
        return self._submit(ApplicationOperation.RETRIEVE, request, idempotency_key)

    def ask(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit grounded answer synthesis work."""
        return self._submit(ApplicationOperation.ASK, request, idempotency_key)

    def research(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit bounded counterevidence research work."""
        return self._submit(ApplicationOperation.RESEARCH, request, idempotency_key)

    def run(
        self,
        request: RuntimeOperationRequest,
        *,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        """Submit one complete linked Runtime run."""
        return self._submit(ApplicationOperation.RUN, request, idempotency_key)

    def replay(
        self,
        request: ReplayOperationRequest,
        *,
        idempotency_key: str,
        timeout_seconds: float | None = None,
    ) -> DurableJobSnapshot:
        """Submit one linked replay with explicit network authority."""
        return self._jobs.submit(
            DurableJobRequest(
                kind=JobKind.REPLAY,
                idempotency_key=idempotency_key,
                payload=replay_request_payload(request),
                timeout_seconds=timeout_seconds,
            )
        )

    def inspect(
        self,
        run_id: str,
        *,
        attempt_id: str | None = None,
    ) -> RuntimeRunInspection:
        """Inspect a persisted run without relying on live process state."""
        return self._inspector.inspect(run_id, attempt_id=attempt_id)

    def inspect_page(
        self,
        run_id: str,
        *,
        attempt_id: str | None = None,
        page: PageRequest,
    ) -> Mapping[str, object]:
        """Inspect bounded collections with a cursor tied to immutable run state."""
        inspection = self.inspect(run_id, attempt_id=attempt_id)
        record = _record(inspection)
        return paginate_collections(
            record,
            collection_fields=(
                "entry_step_ids",
                "terminal_step_ids",
                "attempts",
                "steps",
                "events",
                "artifacts",
                "queries",
                "hits",
                "claims",
                "citations",
                "tool_calls",
                "provider_calls",
                "budgets",
                "checks",
                "failures",
            ),
            resource_identity={
                "attempt_id": record.get("selected_attempt_id"),
                "plan_sha256": record.get("plan_sha256"),
                "run_id": record.get("run_id"),
            },
            request=page,
        )

    def compare(
        self,
        *,
        baseline_run_id: str,
        baseline_attempt_id: str,
        candidate_run_id: str,
        candidate_attempt_id: str,
        policy: RuntimeComparisonPolicy | None = None,
    ) -> RuntimeComparisonResult:
        """Compare persisted attempts through the canonical semantic service."""
        return self._comparison.compare(
            baseline_run_id=baseline_run_id,
            baseline_attempt_id=baseline_attempt_id,
            candidate_run_id=candidate_run_id,
            candidate_attempt_id=candidate_attempt_id,
            policy=policy,
        )

    def compare_page(
        self,
        *,
        baseline_run_id: str,
        baseline_attempt_id: str,
        candidate_run_id: str,
        candidate_attempt_id: str,
        page: PageRequest,
        policy: RuntimeComparisonPolicy | None = None,
    ) -> Mapping[str, object]:
        """Compare attempts with a bounded, snapshot-bound difference page."""
        comparison = self.compare(
            baseline_run_id=baseline_run_id,
            baseline_attempt_id=baseline_attempt_id,
            candidate_run_id=candidate_run_id,
            candidate_attempt_id=candidate_attempt_id,
            policy=policy,
        )
        record = _record(comparison)
        return paginate_collections(
            record,
            collection_fields=("differences",),
            resource_identity={
                "comparison_sha256": record.get("comparison_sha256"),
                "baseline_run_id": baseline_run_id,
                "candidate_run_id": candidate_run_id,
            },
            request=page,
        )

    def status(self, job_id: str) -> DurableJobSnapshot:
        """Return current status directly from the durable job authority."""
        return self._jobs.status(job_id)

    def result(self, job_id: str) -> dict[str, object]:
        """Return one successful durable result or its exact terminal error."""
        return self._jobs.result(job_id)

    def cancel(self, job_id: str) -> DurableJobSnapshot:
        """Persist cancellation through the same authority used by workers."""
        return self._jobs.cancel(job_id)

    def wait(
        self,
        job_id: str,
        *,
        timeout_seconds: float | None = None,
    ) -> DurableJobSnapshot:
        """Wait on durable worker notification for library-owned lifecycles."""

        return self._jobs.wait(job_id, timeout_seconds=timeout_seconds)

    def close(self) -> None:
        """Release worker resources after the application boundary is stopped."""

        self._jobs.close()

    def __enter__(self) -> RuntimeApplicationServicesV2:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _submit(
        self,
        operation: ApplicationOperation,
        request: RuntimeOperationRequest,
        idempotency_key: str,
    ) -> DurableJobSnapshot:
        expected = _METHOD_OPERATIONS[operation]
        if request.operation is not expected:
            raise ValueError(
                f"{operation.value} service requires operation {expected.value}"
            )
        return self._jobs.submit(
            DurableJobRequest(
                kind=JobKind.RUN,
                idempotency_key=idempotency_key,
                payload=runtime_request_payload(request),
                timeout_seconds=request.budget.timeout_seconds,
            )
        )


def _record(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    raise TypeError("application response must be a dataclass or mapping")


__all__ = [
    "ApplicationCapabilityError",
    "ReplayOperationExecutor",
    "ResourceInspectionExecutor",
    "RuntimeApplicationServicesV2",
    "RuntimeOperationExecutor",
    "build_runtime_job_handlers",
]
