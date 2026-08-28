# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed grounded answer synthesis at the Runtime DAG boundary."""

from __future__ import annotations

from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionOutcome,
    GroundingEvidenceState,
    ImmutableEvidenceLocator,
    LocalGroundedAnswerService,
    PacketCompleteness,
    RetrievalEvidenceStatus,
    SemanticEmbeddingService,
    SynthesisOutcome,
    VexEvidenceStatus,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    SUPPORTED_LOCAL_REASON_PROVIDERS,
    ConcreteDagStep,
    DagOperation,
    ExecutionProfile,
)
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    _bounded_output,
    _json_object,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StepDispatchError(f"retrieval evidence field is invalid: {field}")
    return value


def _required_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StepDispatchError(f"retrieval evidence field is invalid: {field}")
    return value


def _required_score(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise StepDispatchError(f"retrieval evidence field is invalid: {field}")
    return float(value)


def _artifact_id_from_digest(value: str, field: str) -> str:
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise StepDispatchError(f"retrieval evidence field is invalid: {field}")
    return f"sha256:{digest}"


def _selectors(value: object) -> tuple[tuple[str, str | int], ...]:
    if not isinstance(value, list) or not value:
        raise StepDispatchError("retrieval evidence locator selectors are invalid")
    result: list[tuple[str, str | int]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or isinstance(item[1], bool)
            or not isinstance(item[1], str | int)
        ):
            raise StepDispatchError("retrieval evidence locator selectors are invalid")
        result.append((item[0], item[1]))
    return tuple(result)


def _locator_evidence_segments(
    raw_hit: dict[str, object],
    *,
    fallback_section_path: tuple[str, ...],
) -> tuple[
    tuple[
        dict[str, object],
        tuple[str, ...],
        str,
        str,
        str,
        str,
    ],
    ...,
]:
    raw_segments = raw_hit.get("locator_segments")
    if isinstance(raw_segments, list) and raw_segments:
        result = []
        hit_artifact_id = _required_string(raw_hit.get("artifact_id"), "artifact_id")
        chunk_id = _required_string(raw_hit.get("chunk_id"), "chunk_id")
        for ordinal, raw_segment in enumerate(raw_segments):
            if not isinstance(raw_segment, dict):
                raise StepDispatchError("retrieval locator segment is invalid")
            raw_locator = raw_segment.get("locator")
            raw_section = raw_segment.get("section_path")
            if not isinstance(raw_locator, dict) or not isinstance(raw_section, list):
                raise StepDispatchError("retrieval locator segment is invalid")
            section_path = tuple(
                _required_string(item, "segment.section_path") for item in raw_section
            )
            if not section_path:
                section_path = fallback_section_path
            exact_text = _required_string(
                raw_segment.get("verbatim_text"), "segment.verbatim_text"
            )
            exact_text_sha256 = _required_string(
                raw_segment.get("content_sha256"), "segment.content_sha256"
            )
            locator_artifact_id = content_artifact_id(
                {
                    "chunk_id": chunk_id,
                    "chunk_span": {
                        "end": _required_int(
                            raw_segment.get("chunk_end"), "segment.chunk_end"
                        ),
                        "start": _required_int(
                            raw_segment.get("chunk_start"), "segment.chunk_start"
                        ),
                    },
                    "locator": raw_locator,
                    "mapping_id": _required_string(
                        raw_segment.get("mapping_id"), "segment.mapping_id"
                    ),
                }
            )
            evidence_artifact_id = content_artifact_id(
                {
                    "locator_artifact_id": locator_artifact_id,
                    "ordinal": ordinal,
                    "retrieval_hit_artifact_id": hit_artifact_id,
                }
            )
            result.append(
                (
                    raw_locator,
                    section_path,
                    exact_text,
                    exact_text_sha256,
                    locator_artifact_id,
                    evidence_artifact_id,
                )
            )
        return tuple(result)
    raw_locator = raw_hit.get("locator")
    if not isinstance(raw_locator, dict):
        raise StepDispatchError("retrieval citation locator is invalid")
    return (
        (
            raw_locator,
            fallback_section_path,
            _required_string(raw_hit.get("verbatim_text"), "verbatim_text"),
            _required_string(raw_hit.get("content_sha256"), "content_sha256"),
            _required_string(raw_hit.get("locator_record_id"), "locator_record_id"),
            _required_string(raw_hit.get("artifact_id"), "artifact_id"),
        ),
    )


def citation_inputs_from_evidence_set(
    evidence_set: dict[str, object],
    *,
    retrieval_artifact_id: str,
    claim_key: str,
) -> tuple[tuple[CitationEvidence, ...], tuple[CitationSourceDescriptor, ...]]:
    raw_hits = evidence_set.get("hits")
    if not isinstance(raw_hits, list):
        raise StepDispatchError("retrieval evidence hits are invalid")
    evidence: list[CitationEvidence] = []
    sources: dict[str, CitationSourceDescriptor] = {}
    try:
        for raw_hit in raw_hits:
            if not isinstance(raw_hit, dict):
                raise StepDispatchError("retrieval evidence hit is invalid")
            raw_source = raw_hit.get("source")
            raw_section = raw_hit.get("section_path")
            if (
                not isinstance(raw_source, dict)
                or not isinstance(raw_section, list)
                or not raw_section
                or any(not isinstance(item, str) or not item for item in raw_section)
            ):
                raise StepDispatchError("retrieval citation metadata is invalid")
            source_id = _required_string(raw_source.get("source_id"), "source_id")
            source_sha256 = _required_string(
                raw_source.get("source_content_sha256"), "source_content_sha256"
            )
            source_uri = _required_string(raw_source.get("source_uri"), "source_uri")
            title = _required_string(raw_source.get("title"), "title")
            doi = raw_source.get("doi")
            if doi is not None and not isinstance(doi, str):
                raise StepDispatchError("retrieval source DOI is invalid")
            raw_authors = raw_source.get("authors", [])
            if not isinstance(raw_authors, list) or any(
                not isinstance(item, str) or not item for item in raw_authors
            ):
                raise StepDispatchError("retrieval source authors are invalid")
            source = CitationSourceDescriptor.create(
                source_id=source_id,
                title=title,
                canonical_uri=source_uri,
                doi=doi,
                source_content_sha256=source_sha256,
                authors=tuple(raw_authors),
                journal=(
                    _required_string(raw_source["journal"], "journal")
                    if raw_source.get("journal") is not None
                    else None
                ),
                publication_date=(
                    _required_string(raw_source["publication_date"], "publication_date")
                    if raw_source.get("publication_date") is not None
                    else None
                ),
                license_expression=(
                    _required_string(raw_source["license_id"], "license_id")
                    if raw_source.get("license_id") is not None
                    else None
                ),
                license_url=(
                    _required_string(raw_source["license_url"], "license_url")
                    if raw_source.get("license_url") is not None
                    else None
                ),
                provenance_artifact_id=(
                    _required_string(
                        raw_source["provenance_artifact_id"],
                        "provenance_artifact_id",
                    )
                    if raw_source.get("provenance_artifact_id") is not None
                    else None
                ),
                format_id=(
                    _required_string(raw_source["format_id"], "format_id")
                    if raw_source.get("format_id") is not None
                    else None
                ),
                language=(
                    _required_string(raw_source["language"], "language")
                    if raw_source.get("language") is not None
                    else None
                ),
            )
            existing = sources.get(source_id)
            if existing is not None and existing != source:
                raise StepDispatchError("retrieval source identities collide")
            sources[source_id] = source
            for (
                raw_locator,
                section_path,
                exact_text,
                exact_text_sha256,
                locator_artifact_id,
                evidence_artifact_id,
            ) in _locator_evidence_segments(
                raw_hit,
                fallback_section_path=tuple(raw_section),
            ):
                evidence.append(
                    CitationEvidence(
                        artifact_id=evidence_artifact_id,
                        chunk_artifact_id=_artifact_id_from_digest(
                            _required_string(raw_hit.get("chunk_id"), "chunk_id"),
                            "chunk_id",
                        ),
                        retrieval_artifact_id=retrieval_artifact_id,
                        document_id=_required_string(
                            raw_hit.get("document_id"), "document_id"
                        ),
                        source_id=source_id,
                        section_path=section_path,
                        locator=ImmutableEvidenceLocator(
                            artifact_id=locator_artifact_id,
                            source_artifact_id=_artifact_id_from_digest(
                                source_sha256, "source_content_sha256"
                            ),
                            source_uri=source_uri,
                            source_content_sha256=source_sha256,
                            scheme=_required_string(
                                raw_locator.get("scheme"), "scheme"
                            ),
                            selectors=_selectors(raw_locator.get("selectors")),
                        ),
                        exact_text=exact_text,
                        exact_text_sha256=exact_text_sha256,
                        rank=_required_int(raw_hit.get("rank"), "rank"),
                        relevance_score=_required_score(
                            raw_hit.get("retrieval_score"), "retrieval_score"
                        ),
                        claim_keys=(claim_key,),
                    )
                )
    except ValidationError as error:
        raise StepDispatchError(
            "retrieval evidence violates Reason contracts"
        ) from error
    return tuple(evidence), tuple(sources[key] for key in sorted(sources))


class CanonicalReasonOperationAdapter:
    """Produce an exact-citation RAG claim graph without requiring credentials."""

    adapter_id = "bijux-canon-reason:grounded-answer:v1"
    adapter_version = "1.0"
    operation = DagOperation.REASON

    def __init__(
        self,
        *,
        semantic_encoder: SemanticEmbeddingService | None = None,
    ) -> None:
        self._semantic_encoder = semantic_encoder

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("reasoning requires one retrieval evidence set")
        if step.inputs.query is None or step.inputs.output_policy is None:
            raise StepDispatchError("reasoning requires query and output policy")
        if step.inputs.provider not in SUPPORTED_LOCAL_REASON_PROVIDERS:
            raise StepDispatchError(
                "provider-backed reasoning requires separately configured credentials"
            )
        retrieval_artifact = upstream_artifacts[0].artifact
        evidence_set = _json_object(retrieval_artifact, "index.evidence-set.v1")
        if evidence_set.get("schema_version") != "bijux.canon.index.evidence_set.v1":
            raise StepDispatchError("retrieval evidence schema is unsupported")
        question_id = content_artifact_id(
            {
                "question": step.inputs.query,
                "schema_version": "bijux.canon.reason.question.v1",
            }
        )
        scope_id = content_artifact_id(
            {
                "schema_version": "bijux.canon.reason.scope.v1",
                "scope": step.inputs.scope,
            }
        )
        candidates, sources = citation_inputs_from_evidence_set(
            evidence_set,
            retrieval_artifact_id=str(retrieval_artifact.descriptor.artifact_id),
            claim_key=question_id,
        )
        citation_budget = max(1, min(len(candidates) or 1, 16))
        packet = EvidencePacketBuilder(
            EvidencePacketPolicy(
                token_budget=max(
                    1, min(8192, step.inputs.budget.max_artifact_bytes // 4)
                ),
                citation_budget=citation_budget,
                claim_budget=citation_budget,
                max_per_source=citation_budget,
                max_per_section=citation_budget,
            )
        ).build(
            question_artifact_id=question_id,
            scope_artifact_id=scope_id,
            retrieval_trace_artifact_ids=(
                str(retrieval_artifact.descriptor.artifact_id),
            ),
            candidates=candidates,
        )
        evidence_state = _grounding_evidence_state(
            evidence_set,
            retrieved_evidence_count=len(candidates),
            selected_evidence_count=len(packet.selected),
            packet_completeness=packet.completeness,
        )
        semantic_encoder = (
            None
            if step.inputs.execution_profile is ExecutionProfile.OFFLINE_LEXICAL
            else self._semantic_encoder
        )
        grounded = LocalGroundedAnswerService(semantic_encoder=semantic_encoder).answer(
            question=step.inputs.query,
            evidence_packet=packet,
            sources=sources,
            max_points=min(citation_budget, 6),
            evidence_state=evidence_state,
        )
        if (
            grounded.synthesis.outcome is SynthesisOutcome.insufficient
            and not step.inputs.output_policy.permit_insufficient_answer
        ):
            raise StepDispatchError("grounded answer has insufficient evidence")
        payload = canonical_json_bytes(
            {
                "answer": grounded.answer_text,
                "answer_disposition": grounded.outcome.value,
                "citation_verification": grounded.verification.model_dump(mode="json"),
                "citations": grounded.citations.model_dump(mode="json"),
                "citation_presentation": grounded.citation_presentation.model_dump(
                    mode="json"
                ),
                "claims": grounded.claims.model_dump(mode="json"),
                "contextualized": grounded.contextualized.model_dump(mode="json"),
                "evidence_packet": packet.model_dump(mode="json"),
                "evidence_state": evidence_state.model_dump(mode="json"),
                "evidence_set_artifact_id": str(
                    retrieval_artifact.descriptor.artifact_id
                ),
                "generation_id": evidence_set.get("generation_id"),
                "index_artifact_id": evidence_set.get("index_artifact_id"),
                "mode": "credential-free-rag-v1",
                "provenance": {
                    "execution_configuration_sha256": evidence_set.get(
                        "execution_configuration_sha256"
                    ),
                    "execution_manifest_artifact_id": (
                        None
                        if context.execution_manifest_artifact_id is None
                        else str(context.execution_manifest_artifact_id)
                    ),
                    "execution_profile": step.inputs.execution_profile.value,
                    "index_artifact_id": evidence_set.get("index_artifact_id"),
                    "model_lock_artifact_id": evidence_set.get(
                        "model_lock_artifact_id"
                    ),
                    "parent_job_id": step.inputs.parent_job_id,
                    "retrieval_artifact_id": str(
                        retrieval_artifact.descriptor.artifact_id
                    ),
                    "run_id": context.run_id,
                    "schema_version": "bijux.runtime.answer-provenance.v1",
                    "snapshot_artifact_id": evidence_set.get("snapshot_artifact_id"),
                    "source_archive_artifact_id": evidence_set.get(
                        "source_archive_artifact_id"
                    ),
                },
                "provider": step.inputs.provider,
                "query": step.inputs.query,
                "schema_version": "bijux.canon.reason.claim_graph.v1",
                "retrieval_filters": evidence_set.get("filters"),
                "grounding_admission": grounded.admission.model_dump(mode="json"),
                "grounded_answer_artifact_id": grounded.artifact_id,
                "sources": [source.model_dump(mode="json") for source in sources],
                "status": _answer_status(grounded.outcome),
                "synthesis": grounded.synthesis.model_dump(mode="json"),
                "synthesis_status": grounded.synthesis.outcome.value,
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="reason.claim-graph.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


def _grounding_evidence_state(
    evidence_set: dict[str, object],
    *,
    retrieved_evidence_count: int,
    selected_evidence_count: int,
    packet_completeness: PacketCompleteness,
) -> GroundingEvidenceState:
    raw_status = _required_string(evidence_set.get("status"), "status")
    try:
        retrieval_status = RetrievalEvidenceStatus(raw_status)
    except ValueError as error:
        raise StepDispatchError("retrieval evidence status is unsupported") from error
    raw_retrieval = evidence_set.get("retrieval")
    if not isinstance(raw_retrieval, dict):
        raise StepDispatchError("retrieval execution evidence is invalid")
    raw_attempts = raw_retrieval.get("vex_attempts", [])
    if not isinstance(raw_attempts, list):
        raise StepDispatchError("retrieval VEX attempts are invalid")
    fallback = raw_retrieval.get("fallback_action")
    if raw_attempts:
        vex_status = (
            VexEvidenceStatus.below_policy
            if retrieval_status is RetrievalEvidenceStatus.refused
            else VexEvidenceStatus.exact_fallback_verified
            if fallback == "bounded-exact-after-ann-refusal"
            else VexEvidenceStatus.verified
        )
    else:
        vex_status = VexEvidenceStatus.not_applicable
    raw_refusal = evidence_set.get("refusal")
    detail = remediation = None
    budget_exhausted = False
    if raw_refusal is not None:
        if not isinstance(raw_refusal, dict):
            raise StepDispatchError("retrieval refusal evidence is invalid")
        detail = _required_string(raw_refusal.get("detail"), "refusal.detail")
        remediation = _required_string(
            raw_refusal.get("remediation"), "refusal.remediation"
        )
        violations = raw_refusal.get("violations", [])
        if not isinstance(violations, list):
            raise StepDispatchError("retrieval refusal violations are invalid")
        budget_exhausted = any(
            isinstance(item, str) and "budget" in item for item in violations
        )
    return GroundingEvidenceState.create(
        retrieval_status=retrieval_status,
        vex_status=vex_status,
        retrieved_evidence_count=retrieved_evidence_count,
        selected_evidence_count=selected_evidence_count,
        packet_completeness=packet_completeness,
        budget_exhausted=budget_exhausted,
        policy_detail=detail,
        remediation=remediation,
    )


def _answer_status(outcome: GroundingAdmissionOutcome) -> str:
    return {
        GroundingAdmissionOutcome.admitted: "answered",
        GroundingAdmissionOutcome.partially_admitted: "partially-abstained",
        GroundingAdmissionOutcome.abstained: "abstained",
    }[outcome]


__all__ = ["CanonicalReasonOperationAdapter", "citation_inputs_from_evidence_set"]
