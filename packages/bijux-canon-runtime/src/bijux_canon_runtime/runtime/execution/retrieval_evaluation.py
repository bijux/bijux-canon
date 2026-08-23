# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed Runtime execution boundary for public retrieval evaluation."""

from __future__ import annotations

from collections.abc import Mapping
import json

from bijux_canon_index.application import IndexService
from bijux_canon_index.evaluation import (
    ObservedLocatorSegment,
    ObservedRetrievalHit,
    PublicRetrievalEvaluationRequest,
    RetrievalExecutionObservation,
    RetrievalExecutionStatus,
    ReviewedRetrievalQuery,
)
from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.application_executor import (
    RuntimeExecutionService,
    RuntimeFirstExecutionError,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)


class InstalledRetrievalEvaluationExecutor:
    """Run truth-only queries through the installed persistent retrieval DAG."""

    def __init__(
        self,
        *,
        execution: RuntimeExecutionService,
        store: AtomicFilesystemArtifactPayloadStore,
        index: IndexService,
    ) -> None:
        self._execution = execution
        self._store = store
        self._index = index

    def execute(
        self,
        request: PublicRetrievalEvaluationRequest,
        query: ReviewedRetrievalQuery,
    ) -> RetrievalExecutionObservation:
        """Execute one query and retain success, refusal, or failure evidence."""

        index_artifact = self._store.load(ArtifactID(request.index_artifact_id))
        prepared = self._index.prepare_archive(index_artifact.canonical_bytes)
        inspection = prepared.inspection
        runtime_request = RuntimeOperationRequest(
            request_id=RequestID(
                f"retrieval-evaluation-{request.request_sha256[:16]}-"
                f"{query.input_identity_sha256[:16]}"
            ),
            operation=RuntimeRequestOperation.RETRIEVE,
            execution_profile=ExecutionProfile(request.mode.value),
            budget=RuntimeRequestBudget(
                timeout_seconds=120.0,
                max_artifact_bytes=64 * 1024 * 1024,
            ),
            replay_mode=ReplayMode.STRICT,
            scope=f"retrieval-evaluation:{request.split}",
            query=query.query_text,
            index_id=ArtifactID(request.index_artifact_id),
            top_k=request.top_k,
        )
        try:
            result = self._execution.execute(runtime_request, lambda: False)
        except RuntimeFirstExecutionError as error:
            message = str(error)
            refused = "VEX policy refused" in message
            return RetrievalExecutionObservation(
                query_id=query.query_id,
                query_text_sha256=_query_sha256(query.query_text),
                status=(
                    RetrievalExecutionStatus.refused
                    if refused
                    else RetrievalExecutionStatus.failed
                ),
                generation_id=inspection.generation_id,
                model_lock_artifact_id=inspection.model_lock_artifact_id,
                configuration_id=inspection.build.configuration_id,
                retrieval_mode=request.mode.value,
                hits=(),
                run_id=None,
                attempt_id=None,
                vex_artifact_id=None,
                policy_action="refuse" if refused else "fail",
                fallback_action="none",
                failure=message,
            )
        terminal_ids = result.get("terminal_artifact_ids")
        if (
            not isinstance(terminal_ids, list)
            or len(terminal_ids) != 1
            or not isinstance(terminal_ids[0], str)
        ):
            raise RuntimeError("retrieval evaluation terminal artifact is invalid")
        artifact = self._store.load(ArtifactID(terminal_ids[0]))
        try:
            evidence = json.loads(artifact.canonical_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("retrieval evaluation evidence is unreadable") from error
        if not isinstance(evidence, dict):
            raise RuntimeError("retrieval evaluation evidence is invalid")
        return _observation(
            request=request,
            query=query,
            result=result,
            evidence=evidence,
            generation_id=inspection.generation_id,
            model_lock_artifact_id=inspection.model_lock_artifact_id,
            configuration_id=inspection.build.configuration_id,
        )


def _observation(
    *,
    request: PublicRetrievalEvaluationRequest,
    query: ReviewedRetrievalQuery,
    result: Mapping[str, object],
    evidence: Mapping[str, object],
    generation_id: str,
    model_lock_artifact_id: str,
    configuration_id: str,
) -> RetrievalExecutionObservation:
    if (
        evidence.get("schema_version") != "bijux.canon.index.evidence_set.v1"
        or evidence.get("generation_id") != generation_id
        or evidence.get("retrieval_mode")
        != request.mode.value.replace("offline-lexical", "lexical")
    ):
        raise RuntimeError("retrieval evaluation evidence provenance diverged")
    raw_hits = evidence.get("hits")
    if not isinstance(raw_hits, list):
        raise RuntimeError("retrieval evaluation hits are invalid")
    hits = tuple(_hit(raw, expected_rank=rank) for rank, raw in enumerate(raw_hits, 1))
    raw_status = evidence.get("status")
    try:
        status = RetrievalExecutionStatus(str(raw_status))
    except ValueError as error:
        raise RuntimeError("retrieval evaluation status is invalid") from error
    retrieval = evidence.get("retrieval")
    if not isinstance(retrieval, dict):
        raise RuntimeError("retrieval evaluation channel evidence is invalid")
    dense = retrieval.get("dense")
    vex_artifact_id: str | None = None
    policy_action = "not-applicable"
    if dense is not None:
        if not isinstance(dense, dict):
            raise RuntimeError("retrieval evaluation dense evidence is invalid")
        raw_vex_id = dense.get("artifact_id")
        decision = dense.get("decision")
        if not isinstance(raw_vex_id, str) or not isinstance(decision, dict):
            raise RuntimeError("retrieval evaluation VEX evidence is invalid")
        raw_action = decision.get("status")
        if not isinstance(raw_action, str) or not raw_action:
            raise RuntimeError("retrieval evaluation VEX decision is invalid")
        vex_artifact_id = raw_vex_id
        policy_action = raw_action
    run_id = result.get("run_id")
    attempt_id = result.get("attempt_id")
    if not isinstance(run_id, str) or not isinstance(attempt_id, str):
        raise RuntimeError("retrieval evaluation Runtime lineage is invalid")
    return RetrievalExecutionObservation(
        query_id=query.query_id,
        query_text_sha256=_required_string(evidence, "query_text_sha256"),
        status=status,
        generation_id=generation_id,
        model_lock_artifact_id=model_lock_artifact_id,
        configuration_id=configuration_id,
        retrieval_mode=_required_string(evidence, "retrieval_mode"),
        hits=hits,
        run_id=run_id,
        attempt_id=attempt_id,
        vex_artifact_id=vex_artifact_id,
        policy_action=policy_action,
        fallback_action="none",
        failure=None,
    )


def _hit(value: object, *, expected_rank: int) -> ObservedRetrievalHit:
    if not isinstance(value, dict):
        raise RuntimeError("retrieval evaluation hit is invalid")
    source = value.get("source")
    raw_segments = value.get("locator_segments")
    if not isinstance(source, dict) or not isinstance(raw_segments, list):
        raise RuntimeError("retrieval evaluation hit lineage is invalid")
    segments = tuple(_locator_segment(item) for item in raw_segments)
    rank = _required_int(value, "rank")
    if rank != expected_rank:
        raise RuntimeError("retrieval evaluation hit ranks are not contiguous")
    score = value.get("retrieval_score")
    if isinstance(score, bool) or not isinstance(score, int | float):
        raise RuntimeError("retrieval evaluation hit score is invalid")
    return ObservedRetrievalHit(
        rank=rank,
        retrieval_rank=_required_int(value, "retrieval_rank"),
        score=float(score),
        chunk_id=_required_string(value, "chunk_id"),
        document_id=_required_string(value, "document_id"),
        source_content_sha256=_required_string(source, "source_content_sha256"),
        content_sha256=_required_string(value, "content_sha256"),
        locator_segments=segments,
    )


def _locator_segment(value: object) -> ObservedLocatorSegment:
    if not isinstance(value, dict):
        raise RuntimeError("retrieval evaluation locator segment is invalid")
    locator = value.get("locator")
    if not isinstance(locator, dict):
        raise RuntimeError("retrieval evaluation exact locator is invalid")
    raw_selectors = locator.get("selectors")
    if not isinstance(raw_selectors, list):
        raise RuntimeError("retrieval evaluation locator selectors are invalid")
    selectors: list[tuple[str, str | int]] = []
    for item in raw_selectors:
        if (
            not isinstance(item, list | tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or isinstance(item[1], bool)
            or not isinstance(item[1], str | int)
        ):
            raise RuntimeError("retrieval evaluation locator selector is invalid")
        selectors.append((item[0], item[1]))
    return ObservedLocatorSegment(
        ordinal=_required_int(value, "ordinal"),
        mapping_id=_required_string(value, "mapping_id"),
        scheme=_required_string(locator, "scheme"),
        selectors=tuple(selectors),
        content_sha256=_required_string(value, "content_sha256"),
    )


def _required_string(value: Mapping[str, object], field: str) -> str:
    selected = value.get(field)
    if not isinstance(selected, str) or not selected:
        raise RuntimeError(f"retrieval evaluation field is invalid: {field}")
    return selected


def _required_int(value: Mapping[str, object], field: str) -> int:
    selected = value.get(field)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise RuntimeError(f"retrieval evaluation integer is invalid: {field}")
    return selected


def _query_sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = ["InstalledRetrievalEvaluationExecutor"]
