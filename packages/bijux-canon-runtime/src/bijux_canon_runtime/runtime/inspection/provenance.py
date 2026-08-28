# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Fail-closed traversal from Runtime results to retained source bytes."""

from __future__ import annotations

import hashlib

from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection.models import (
    InspectedArtifact,
    InspectedAttempt,
    InspectedCitationProvenance,
    InspectedDagStep,
    InspectedRunProvenance,
    RuntimeInspectionError,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    json_object,
    required_dict,
    required_list,
    required_object,
    required_string,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    PayloadCorruptionError,
)
from bijux_canon_runtime.runtime.persistence.payload_store import (
    DurableArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.source_archive import (
    SourceArchiveError,
    read_source_archive,
)


def resolve_run_provenance(
    *,
    run_id: str,
    selected_attempt: InspectedAttempt,
    steps: tuple[InspectedDagStep, ...],
    artifacts: tuple[InspectedArtifact, ...],
    store: DurableArtifactPayloadStore,
    attempts: tuple[InspectedAttempt, ...] = (),
) -> InspectedRunProvenance:
    """Validate causal edges and resolve every emitted citation to source bytes."""
    by_id = {item.artifact_id: item for item in artifacts}
    legacy_lineage = not any(
        item.schema_id == "ingest.source-archive.v1" for item in artifacts
    )
    _validate_step_dependencies(
        steps,
        by_id,
        permit_legacy_external_inputs=legacy_lineage,
    )
    manifest = _json_artifact(by_id, selected_attempt.manifest_artifact_id)
    plan = required_object(manifest, "plan")
    execution_metadata = required_object(manifest, "execution_metadata")
    raw_parent_job_id = execution_metadata.get("parent_job_id")
    if raw_parent_job_id is not None and not isinstance(raw_parent_job_id, str):
        raise RuntimeInspectionError("parent job identity is invalid")
    configuration_id = _execution_configuration_identity(
        plan,
        permit_missing=legacy_lineage,
    )
    snapshot_ids = tuple(
        sorted(
            item.artifact_id
            for item in artifacts
            if item.schema_id == "ingest.corpus-snapshot.v1"
        )
    )
    source_archive_ids = tuple(
        sorted(
            item.artifact_id
            for item in artifacts
            if item.schema_id == "ingest.source-archive.v1"
        )
    )
    index_ids = tuple(
        sorted(
            item.artifact_id
            for item in artifacts
            if item.schema_id in {"index.lexical.v1", "index.composite.v1"}
        )
    )
    resolved: list[InspectedCitationProvenance] = []
    model_ids: set[str] = set()
    legacy_citation_count = 0
    for claim_artifact in artifacts:
        if claim_artifact.schema_id != "reason.claim-graph.v1":
            continue
        claim = _json_value(claim_artifact)
        if legacy_lineage and "provenance" not in claim:
            citations = required_object(claim, "citations")
            legacy_citation_count += len(required_list(citations, "links"))
            continue
        provenance = required_object(claim, "provenance")
        claim_parent_job_id = _validate_claim_execution_context(
            provenance=provenance,
            run_id=run_id,
            selected_attempt=selected_attempt,
            selected_parent_job_id=raw_parent_job_id,
            configuration_id=configuration_id,
            store=store,
            attempts=attempts,
        )
        raw_model_id = provenance.get("model_lock_artifact_id")
        if raw_model_id is not None:
            if not isinstance(raw_model_id, str) or not raw_model_id:
                raise RuntimeInspectionError("claim graph model identity is invalid")
            model_ids.add(raw_model_id)
        citations = required_object(claim, "citations")
        for raw_citation in required_list(citations, "links"):
            citation = required_dict(raw_citation, "citation link")
            resolved.append(
                _resolve_citation(
                    citation=citation,
                    claim_artifact=claim_artifact,
                    provenance=provenance,
                    configuration_id=configuration_id,
                    run_id=run_id,
                    parent_job_id=claim_parent_job_id,
                    by_id=by_id,
                    store=store,
                )
            )
    return InspectedRunProvenance(
        status="legacy-unresolved" if legacy_lineage else "verified",
        run_id=run_id,
        execution_manifest_artifact_id=selected_attempt.manifest_artifact_id,
        execution_configuration_sha256=configuration_id,
        parent_job_id=raw_parent_job_id,
        corpus_snapshot_artifact_ids=snapshot_ids,
        source_archive_artifact_ids=source_archive_ids,
        index_artifact_ids=index_ids,
        model_lock_artifact_ids=tuple(sorted(model_ids)),
        citation_count=(legacy_citation_count if legacy_lineage else len(resolved)),
        citations=tuple(resolved),
    )


def _validate_claim_execution_context(
    *,
    provenance: dict[str, object],
    run_id: str,
    selected_attempt: InspectedAttempt,
    selected_parent_job_id: str | None,
    configuration_id: str,
    store: DurableArtifactPayloadStore,
    attempts: tuple[InspectedAttempt, ...],
) -> str | None:
    if (
        provenance.get("run_id") != run_id
        or provenance.get("execution_configuration_sha256") != configuration_id
    ):
        raise RuntimeInspectionError("claim graph execution provenance is inconsistent")
    claim_manifest_id = provenance.get("execution_manifest_artifact_id")
    claim_parent_job_id = provenance.get("parent_job_id")
    if not isinstance(claim_manifest_id, str) or (
        claim_parent_job_id is not None and not isinstance(claim_parent_job_id, str)
    ):
        raise RuntimeInspectionError("claim graph execution provenance is inconsistent")
    if selected_attempt.relation != "replay":
        if (
            claim_manifest_id != str(selected_attempt.manifest_artifact_id)
            or claim_parent_job_id != selected_parent_job_id
        ):
            raise RuntimeInspectionError(
                "claim graph execution provenance is inconsistent"
            )
        return claim_parent_job_id
    if selected_attempt.source_attempt_id is None:
        raise RuntimeInspectionError("replay claim source attempt is unavailable")
    try:
        source_manifest_artifact = store.load(ArtifactID(claim_manifest_id))
    except (KeyError, PayloadCorruptionError, ValueError) as error:
        raise RuntimeInspectionError(
            "replay claim source manifest is unavailable"
        ) from error
    if source_manifest_artifact.descriptor.schema_id != (
        "bijux.runtime.execution-manifest.v1"
    ):
        raise RuntimeInspectionError("replay claim source manifest is invalid")
    source_manifest = json_object(source_manifest_artifact)
    source_attempt = required_object(source_manifest, "attempt")
    source_metadata = required_object(source_manifest, "execution_metadata")
    source_plan = required_object(source_manifest, "plan")
    claim_source_attempt_id = required_string(source_attempt, "attempt_id")
    by_attempt_id = {item.attempt_id: item for item in attempts}
    ancestor_id: str | None = selected_attempt.source_attempt_id
    source_is_ancestor = False
    while ancestor_id is not None:
        ancestor = by_attempt_id.get(ancestor_id)
        if ancestor is None:
            break
        if ancestor_id == claim_source_attempt_id:
            source_is_ancestor = ancestor.manifest_artifact_id == ArtifactID(
                claim_manifest_id
            )
            break
        ancestor_id = (
            ancestor.source_attempt_id if ancestor.relation == "replay" else None
        )
    if (
        source_manifest.get("run_id") != run_id
        or not source_is_ancestor
        or source_metadata.get("parent_job_id") != claim_parent_job_id
        or _execution_configuration_identity(source_plan, permit_missing=False)
        != configuration_id
    ):
        raise RuntimeInspectionError("replay claim source provenance is inconsistent")
    return claim_parent_job_id


def _validate_step_dependencies(
    steps: tuple[InspectedDagStep, ...],
    by_id: dict[ArtifactID, InspectedArtifact],
    *,
    permit_legacy_external_inputs: bool,
) -> None:
    for step in steps:
        expected = tuple(sorted(step.input_artifact_ids))
        for output_id in step.output_artifact_ids:
            artifact = by_id.get(output_id)
            if artifact is None:
                raise RuntimeInspectionError(
                    f"step {step.step_id} output causal dependencies are invalid"
                )
            if artifact.dependency_artifact_ids == expected:
                continue
            if (
                permit_legacy_external_inputs
                and not expected
                and not step.depends_on
                and artifact.dependency_artifact_ids
            ):
                continue
            raise RuntimeInspectionError(
                f"step {step.step_id} output causal dependencies are invalid"
            )


def _execution_configuration_identity(
    plan: dict[str, object], *, permit_missing: bool
) -> str:
    identities: set[str] = set()
    for raw_step in required_list(plan, "steps"):
        step = required_dict(raw_step, "plan step")
        inputs = required_object(step, "inputs")
        raw_value = inputs.get("execution_configuration_sha256")
        if raw_value is None and permit_missing:
            continue
        value = required_string(inputs, "execution_configuration_sha256")
        identities.add(value)
    if not identities and permit_missing:
        return "legacy-unbound"
    if len(identities) != 1:
        raise RuntimeInspectionError(
            "Runtime plan execution configuration identities diverge"
        )
    return identities.pop()


def _resolve_citation(
    *,
    citation: dict[str, object],
    claim_artifact: InspectedArtifact,
    provenance: dict[str, object],
    configuration_id: str,
    run_id: str,
    parent_job_id: str | None,
    by_id: dict[ArtifactID, InspectedArtifact],
    store: DurableArtifactPayloadStore,
) -> InspectedCitationProvenance:
    citation_id = required_string(citation, "artifact_id")
    retrieval_id = ArtifactID(required_string(citation, "retrieval_artifact_id"))
    if provenance.get("retrieval_artifact_id") != str(retrieval_id):
        raise RuntimeInspectionError("citation retrieval provenance is inconsistent")
    retrieval_artifact = by_id.get(retrieval_id)
    if retrieval_artifact is None or retrieval_artifact.schema_id != (
        "index.evidence-set.v1"
    ):
        raise RuntimeInspectionError("citation retrieval artifact is unavailable")
    retrieval = _json_value(retrieval_artifact)
    index_id = ArtifactID(required_string(retrieval, "index_artifact_id"))
    snapshot_id = ArtifactID(required_string(retrieval, "snapshot_artifact_id"))
    archive_id = ArtifactID(required_string(retrieval, "source_archive_artifact_id"))
    if (
        provenance.get("index_artifact_id") != str(index_id)
        or provenance.get("snapshot_artifact_id") != str(snapshot_id)
        or provenance.get("source_archive_artifact_id") != str(archive_id)
        or retrieval.get("execution_configuration_sha256") != configuration_id
        or retrieval.get("model_lock_artifact_id")
        != provenance.get("model_lock_artifact_id")
    ):
        raise RuntimeInspectionError("citation index provenance is inconsistent")
    _require_dependency(claim_artifact, retrieval_id, "claim graph")
    _require_dependency(retrieval_artifact, index_id, "retrieval evidence")
    if not _dependency_reaches(index_id, snapshot_id, by_id):
        raise RuntimeInspectionError(
            "citation index does not reach its corpus snapshot"
        )
    snapshot_artifact = by_id.get(snapshot_id)
    if snapshot_artifact is None or snapshot_artifact.schema_id != (
        "ingest.corpus-snapshot.v1"
    ):
        raise RuntimeInspectionError("citation corpus snapshot is unavailable")
    _require_dependency(snapshot_artifact, archive_id, "corpus snapshot")
    snapshot = _json_value(snapshot_artifact)
    if snapshot.get("source_archive_artifact_id") != str(archive_id):
        raise RuntimeInspectionError("snapshot source archive identity is inconsistent")
    archive_artifact = by_id.get(archive_id)
    if archive_artifact is None or archive_artifact.schema_id != (
        "ingest.source-archive.v1"
    ):
        raise RuntimeInspectionError("citation source archive is unavailable")
    try:
        archive_entries = read_source_archive(store.load(archive_id).canonical_bytes)
    except (KeyError, SourceArchiveError, ValueError) as error:
        raise RuntimeInspectionError(
            "citation source archive integrity failed"
        ) from error
    document_id = required_string(citation, "document_id")
    chunk_id = required_string(citation, "chunk_artifact_id")
    source_sha256 = required_string(citation, "source_content_sha256")
    document = _snapshot_document(snapshot, document_id, chunk_id)
    metadata = required_object(document, "metadata")
    relative_path = required_string(metadata, "relative_path")
    if metadata.get("source_content_sha256") != source_sha256:
        raise RuntimeInspectionError("citation source digest differs from snapshot")
    entries = tuple(
        item
        for item in archive_entries
        if item.relative_path == relative_path and item.content_sha256 == source_sha256
    )
    if len(entries) != 1:
        raise RuntimeInspectionError("citation source bytes are unresolved")
    spans = _citation_source_spans(document, citation, entries[0].content)
    return InspectedCitationProvenance(
        citation_id=citation_id,
        claim_graph_artifact_id=claim_artifact.artifact_id,
        retrieval_artifact_id=retrieval_id,
        index_artifact_id=index_id,
        corpus_snapshot_artifact_id=snapshot_id,
        source_archive_artifact_id=archive_id,
        chunk_id=chunk_id,
        document_id=document_id,
        source_relative_path=relative_path,
        source_content_sha256=source_sha256,
        source_byte_spans=spans,
        model_lock_artifact_id=(
            None
            if provenance.get("model_lock_artifact_id") is None
            else required_string(provenance, "model_lock_artifact_id")
        ),
        execution_configuration_sha256=configuration_id,
        run_id=run_id,
        parent_job_id=parent_job_id,
    )


def _snapshot_document(
    snapshot: dict[str, object], document_id: str, chunk_id: str
) -> dict[str, object]:
    candidates = []
    for raw_document in required_list(snapshot, "documents"):
        document = required_dict(raw_document, "snapshot document")
        chunks = required_list(document, "chunks")
        if document.get("document_id") == document_id and any(
            isinstance(raw, dict) and raw.get("chunk_id") == chunk_id for raw in chunks
        ):
            candidates.append(document)
    if len(candidates) != 1:
        raise RuntimeInspectionError("citation chunk is unresolved in snapshot")
    return candidates[0]


def _citation_source_spans(
    document: dict[str, object],
    citation: dict[str, object],
    source_bytes: bytes,
) -> tuple[tuple[int, int], ...]:
    raw_selectors = required_list(citation, "locator_selectors")
    selectors: dict[str, object] = {}
    for raw_selector in raw_selectors:
        if (
            not isinstance(raw_selector, list)
            or len(raw_selector) != 2
            or not isinstance(raw_selector[0], str)
        ):
            raise RuntimeInspectionError("citation locator selectors are invalid")
        selectors[raw_selector[0]] = raw_selector[1]
    lineage = required_object(document, "citation_lineage")
    chunk_id = required_string(citation, "chunk_artifact_id")
    spans: set[tuple[int, int]] = set()
    for raw_record in required_list(lineage, "records"):
        record = required_dict(raw_record, "citation lineage record")
        if record.get("chunk_id") != chunk_id:
            continue
        for raw_segment in required_list(record, "segments"):
            segment = required_dict(raw_segment, "citation lineage segment")
            locator = required_object(segment, "locator")
            if (
                locator.get("scheme") != citation.get("locator_scheme")
                or locator.get("selectors") != selectors
            ):
                continue
            source_span = required_object(segment, "source_span")
            start = source_span.get("start")
            end = source_span.get("end")
            selected_sha256 = source_span.get("selected_bytes_sha256")
            if (
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or not 0 <= start <= end <= len(source_bytes)
                or hashlib.sha256(source_bytes[start:end]).hexdigest()
                != selected_sha256
            ):
                raise RuntimeInspectionError("citation source byte span is invalid")
            spans.add((start, end))
    if not spans:
        raise RuntimeInspectionError("citation locator has no immutable source span")
    exact_text = required_string(citation, "exact_text")
    if hashlib.sha256(exact_text.encode("utf-8")).hexdigest() != citation.get(
        "exact_text_sha256"
    ):
        raise RuntimeInspectionError("citation exact text digest is invalid")
    return tuple(sorted(spans))


def _dependency_reaches(
    start: ArtifactID,
    target: ArtifactID,
    by_id: dict[ArtifactID, InspectedArtifact],
) -> bool:
    pending = [start]
    seen: set[ArtifactID] = set()
    while pending:
        artifact_id = pending.pop()
        if artifact_id == target:
            return True
        if artifact_id in seen:
            continue
        seen.add(artifact_id)
        artifact = by_id.get(artifact_id)
        if artifact is not None:
            pending.extend(artifact.dependency_artifact_ids)
    return False


def _require_dependency(
    artifact: InspectedArtifact, dependency_id: ArtifactID, owner: str
) -> None:
    if dependency_id not in artifact.dependency_artifact_ids:
        raise RuntimeInspectionError(f"{owner} causal dependency is missing")


def _json_artifact(
    by_id: dict[ArtifactID, InspectedArtifact], artifact_id: ArtifactID
) -> dict[str, object]:
    artifact = by_id.get(artifact_id)
    if artifact is None:
        raise RuntimeInspectionError("provenance artifact is unavailable")
    return _json_value(artifact)


def _json_value(artifact: InspectedArtifact) -> dict[str, object]:
    return required_dict(artifact.json_value, artifact.schema_id)


__all__ = ["resolve_run_provenance"]
