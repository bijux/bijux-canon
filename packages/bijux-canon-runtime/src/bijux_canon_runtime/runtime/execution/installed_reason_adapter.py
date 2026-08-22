# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed grounded answer synthesis at the Runtime DAG boundary."""

from __future__ import annotations

from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    AtomicClaimNormalizer,
    CitationEvidence,
    CitationSourceDescriptor,
    ClaimCitationLinker,
    CredentialFreeSynthesisPolicy,
    CredentialFreeSynthesizer,
    DeterministicCitationVerifier,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    SynthesisOutcome,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
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

_LOCAL_PROVIDERS = frozenset({"credential-free", "local-recorded"})


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


def _citation_inputs(
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
            raw_locator = raw_hit.get("locator")
            raw_section = raw_hit.get("section_path")
            if (
                not isinstance(raw_source, dict)
                or not isinstance(raw_locator, dict)
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
            source = CitationSourceDescriptor.create(
                source_id=source_id,
                title=title,
                canonical_uri=source_uri,
                doi=doi,
                source_content_sha256=source_sha256,
            )
            existing = sources.get(source_id)
            if existing is not None and existing != source:
                raise StepDispatchError("retrieval source identities collide")
            sources[source_id] = source
            exact_text = _required_string(raw_hit.get("verbatim_text"), "verbatim_text")
            evidence.append(
                CitationEvidence(
                    artifact_id=_required_string(
                        raw_hit.get("artifact_id"), "artifact_id"
                    ),
                    chunk_artifact_id=_artifact_id_from_digest(
                        _required_string(raw_hit.get("chunk_id"), "chunk_id"),
                        "chunk_id",
                    ),
                    retrieval_artifact_id=retrieval_artifact_id,
                    document_id=_required_string(
                        raw_hit.get("document_id"), "document_id"
                    ),
                    source_id=source_id,
                    section_path=tuple(raw_section),
                    locator=ImmutableEvidenceLocator(
                        artifact_id=_required_string(
                            raw_hit.get("locator_record_id"), "locator_record_id"
                        ),
                        source_artifact_id=_artifact_id_from_digest(
                            source_sha256, "source_content_sha256"
                        ),
                        source_uri=source_uri,
                        source_content_sha256=source_sha256,
                        scheme=_required_string(raw_locator.get("scheme"), "scheme"),
                        selectors=_selectors(raw_locator.get("selectors")),
                    ),
                    exact_text=exact_text,
                    exact_text_sha256=_required_string(
                        raw_hit.get("content_sha256"), "content_sha256"
                    ),
                    rank=_required_int(raw_hit.get("rank"), "rank"),
                    relevance_score=_required_score(
                        raw_hit.get("retrieval_score"), "retrieval_score"
                    ),
                    claim_keys=(claim_key,),
                )
            )
    except ValidationError as error:
        raise StepDispatchError("retrieval evidence violates Reason contracts") from error
    return tuple(evidence), tuple(sources[key] for key in sorted(sources))


class CanonicalReasonOperationAdapter:
    """Produce an exact-citation RAG claim graph without requiring credentials."""

    adapter_id = "bijux-canon-reason:grounded-answer:v1"
    adapter_version = "1.0"
    operation = DagOperation.REASON

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
        if step.inputs.provider not in _LOCAL_PROVIDERS:
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
        candidates, sources = _citation_inputs(
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
        synthesis = CredentialFreeSynthesizer(
            CredentialFreeSynthesisPolicy(
                max_points=citation_budget,
                required_sources=2,
            )
        ).synthesize(question=step.inputs.query, evidence_packet=packet)
        if (
            synthesis.outcome is SynthesisOutcome.insufficient
            and not step.inputs.output_policy.permit_insufficient_answer
        ):
            raise StepDispatchError("grounded answer has insufficient evidence")
        claims = AtomicClaimNormalizer().normalize_credential_free(synthesis)
        citations = ClaimCitationLinker().link(
            claim_set=claims,
            evidence_packet=packet,
            sources=sources,
        )
        verification = DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=citations,
        )
        payload = canonical_json_bytes(
            {
                "answer": synthesis.answer_text,
                "citation_verification": verification.model_dump(mode="json"),
                "citations": citations.model_dump(mode="json"),
                "claims": claims.model_dump(mode="json"),
                "evidence_packet": packet.model_dump(mode="json"),
                "evidence_set_artifact_id": str(
                    retrieval_artifact.descriptor.artifact_id
                ),
                "mode": "credential-free-rag-v1",
                "provider": step.inputs.provider,
                "query": step.inputs.query,
                "schema_version": "bijux.canon.reason.claim_graph.v1",
                "sources": [source.model_dump(mode="json") for source in sources],
                "status": synthesis.outcome.value,
                "synthesis": synthesis.model_dump(mode="json"),
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


__all__ = ["CanonicalReasonOperationAdapter"]
