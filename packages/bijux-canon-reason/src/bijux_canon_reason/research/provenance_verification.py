# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Verify final research claims against exact admitted graph evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from enum import StrEnum
import hashlib
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.evidence_packets import CitationEvidence, EvidencePacket
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.assumptions_insufficiency import (
    AssumptionInsufficiencyDelta,
    AssumptionStatus,
    ResearchDeficiencyStatus,
)
from bijux_canon_reason.research.claim_merging import ClaimMergeResult
from bijux_canon_reason.research.convergence import ConvergenceDecision
from bijux_canon_reason.research.evidence_relations import (
    EvidenceRelationAttachment,
    EvidenceRelationKind,
    GraphEvidenceRelation,
)
from bijux_canon_reason.research.graph_synthesis import (
    ResearchSynthesisOutcome,
    SynthesisConfidenceLevel,
    SynthesizedGraphClaim,
    VerifiedGraphSynthesis,
)


class ReasoningProvenanceErrorCode(StrEnum):
    """Stable fail-closed provenance verification outcomes."""

    source_identity_mismatch = "source_identity_mismatch"
    graph_identity_mismatch = "graph_identity_mismatch"
    digest_mismatch = "digest_mismatch"
    artifact_identity_mismatch = "artifact_identity_mismatch"
    dependency_cycle = "dependency_cycle"
    orphan_claim = "orphan_claim"
    unadmitted_evidence = "unadmitted_evidence"
    relation_trace_mismatch = "relation_trace_mismatch"
    unsupported_confidence = "unsupported_confidence"


class ReasoningProvenanceError(ValueError):
    """A final answer cannot be resolved to trustworthy admitted evidence."""

    def __init__(self, code: ReasoningProvenanceErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class EvidenceProvenancePath(StableModel):
    """Exact final-claim to immutable evidence path through verified graph edges."""

    artifact_id: str
    synthesized_claim_artifact_id: str
    canonical_claim_artifact_id: str
    source_claim_artifact_id: str
    evidence_relation_artifact_id: str
    relation_trace_artifact_id: str
    evidence_packet_artifact_id: str
    evidence_artifact_id: str
    locator_artifact_id: str
    source_artifact_id: str
    source_content_sha256: str
    exact_text_sha256: str
    relation: EvidenceRelationKind

    @field_validator(
        "artifact_id",
        "synthesized_claim_artifact_id",
        "canonical_claim_artifact_id",
        "source_claim_artifact_id",
        "evidence_relation_artifact_id",
        "relation_trace_artifact_id",
        "evidence_packet_artifact_id",
        "evidence_artifact_id",
        "locator_artifact_id",
        "source_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_path(self) -> Self:
        for digest in (self.source_content_sha256, self.exact_text_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("provenance path digests must be lowercase SHA-256")
        if self.source_artifact_id != f"sha256:{self.source_content_sha256}":
            raise ValueError("source artifact identity must match source content digest")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("evidence provenance path identity does not match")
        return self


class ClaimProvenanceResolution(StableModel):
    """Complete evidence resolution for one final substantive claim."""

    artifact_id: str
    synthesized_claim_artifact_id: str
    canonical_claim_artifact_id: str
    evidence_path_artifact_ids: tuple[str, ...]
    support_path_count: int
    opposition_path_count: int
    ambiguous_path_count: int

    @field_validator(
        "artifact_id", "synthesized_claim_artifact_id", "canonical_claim_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("evidence_path_artifact_ids")
    @classmethod
    def _validate_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or tuple(sorted(set(value))) != value:
            raise ValueError("claim provenance requires unique sorted evidence paths")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_resolution(self) -> Self:
        counts = (
            self.support_path_count,
            self.opposition_path_count,
            self.ambiguous_path_count,
        )
        if self.support_path_count <= 0 or any(item < 0 for item in counts):
            raise ValueError("final substantive claims require a support path")
        if sum(counts) != len(self.evidence_path_artifact_ids):
            raise ValueError("provenance path counts must be complete")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("claim provenance resolution identity does not match")
        return self


class ReasoningProvenanceReport(StableModel):
    """Content-addressed proof that every final claim resolves exactly."""

    schema_version: Literal["bijux.canon.reason.reasoning_provenance_report.v1"] = (
        "bijux.canon.reason.reasoning_provenance_report.v1"
    )
    artifact_id: str
    synthesis_artifact_id: str
    graph_artifact_id: str
    evidence_packet_artifact_id: str
    claim_merge_artifact_id: str
    evidence_relation_attachment_artifact_id: str
    assumption_insufficiency_artifact_id: str
    convergence_decision_artifact_id: str
    evidence_paths: tuple[EvidenceProvenancePath, ...]
    claim_resolutions: tuple[ClaimProvenanceResolution, ...]
    verified_evidence_artifact_ids: tuple[str, ...]
    synthesis_outcome: ResearchSynthesisOutcome

    @field_validator(
        "artifact_id",
        "synthesis_artifact_id",
        "graph_artifact_id",
        "evidence_packet_artifact_id",
        "claim_merge_artifact_id",
        "evidence_relation_attachment_artifact_id",
        "assumption_insufficiency_artifact_id",
        "convergence_decision_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("verified_evidence_artifact_ids")
    @classmethod
    def _validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("verified evidence identities must be unique and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        path_ids = tuple(item.artifact_id for item in self.evidence_paths)
        if tuple(sorted(set(path_ids))) != path_ids:
            raise ValueError("provenance paths must be unique and sorted")
        resolved_paths = {
            path_id
            for resolution in self.claim_resolutions
            for path_id in resolution.evidence_path_artifact_ids
        }
        if resolved_paths != set(path_ids):
            raise ValueError("claim resolutions must account for every evidence path")
        resolved_evidence = tuple(
            sorted({item.evidence_artifact_id for item in self.evidence_paths})
        )
        if resolved_evidence != self.verified_evidence_artifact_ids:
            raise ValueError("verified evidence identities must equal resolved paths")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("reasoning provenance report identity does not match")
        return self


class ReasoningProvenanceVerifier:
    """Independently resolve and verify a terminal synthesis graph."""

    def verify(
        self,
        *,
        synthesis: VerifiedGraphSynthesis,
        evidence_packet: EvidencePacket,
        claim_merge: ClaimMergeResult,
        evidence_relations: EvidenceRelationAttachment,
        assumption_insufficiency: AssumptionInsufficiencyDelta,
        convergence: ConvergenceDecision,
    ) -> ReasoningProvenanceReport:
        """Return exact paths or fail on any graph, evidence, or confidence defect."""

        self._verify_source_links(
            synthesis,
            claim_merge,
            evidence_relations,
            assumption_insufficiency,
            convergence,
        )
        self._verify_graph_identities(
            synthesis,
            claim_merge,
            evidence_relations,
            assumption_insufficiency,
            convergence,
        )
        evidence_by_id = self._verify_evidence(evidence_packet)
        canonical_ids = {item.artifact_id for item in claim_merge.canonical_claims}
        source_to_canonical = {
            item.source_claim_artifact_id: item.canonical_claim_artifact_id
            for item in claim_merge.mappings
        }
        self._verify_dependencies(claim_merge, canonical_ids)

        def resolve(claim_id: str) -> str:
            if claim_id in canonical_ids:
                return claim_id
            try:
                return source_to_canonical[claim_id]
            except KeyError as error:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.orphan_claim,
                    f"claim {claim_id} is orphaned from canonical graph state",
                ) from error

        relations_by_canonical = defaultdict(list)
        traces_by_relation = {}
        for trace in evidence_relations.traces:
            if trace.relation_artifact_id in traces_by_relation:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.relation_trace_mismatch,
                    "a relation has more than one verification trace",
                )
            traces_by_relation[trace.relation_artifact_id] = trace
        for relation in evidence_relations.relations:
            canonical_id = resolve(relation.claim_artifact_id)
            if relation.evidence_artifact_id not in evidence_by_id:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.unadmitted_evidence,
                    "a graph relation references evidence outside the admitted packet",
                )
            trace = traces_by_relation.get(relation.artifact_id)
            if (
                trace is None
                or trace.citation_evidence_artifact_id
                != relation.evidence_artifact_id
            ):
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.relation_trace_mismatch,
                    "every evidence relation requires one matching verification trace",
                )
            relations_by_canonical[canonical_id].append(relation)
        if set(traces_by_relation) != {
            item.artifact_id for item in evidence_relations.relations
        }:
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.relation_trace_mismatch,
                "relation traces and admitted relations do not correspond exactly",
            )

        final_claims = synthesis.consensus + synthesis.conflicted_claims
        paths = []
        resolutions = []
        for claim in final_claims:
            if claim.canonical_claim_artifact_id not in canonical_ids:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.orphan_claim,
                    "a final substantive claim is absent from canonical graph state",
                )
            relations = tuple(relations_by_canonical[claim.canonical_claim_artifact_id])
            self._verify_claim_edges(claim, relations)
            self._verify_confidence(
                claim,
                relations,
                synthesis,
                assumption_insufficiency,
                resolve,
            )
            claim_paths = []
            for relation in relations:
                evidence = evidence_by_id[relation.evidence_artifact_id]
                trace = traces_by_relation[relation.artifact_id]
                payload = {
                    "synthesized_claim_artifact_id": claim.artifact_id,
                    "canonical_claim_artifact_id": claim.canonical_claim_artifact_id,
                    "source_claim_artifact_id": relation.claim_artifact_id,
                    "evidence_relation_artifact_id": relation.artifact_id,
                    "relation_trace_artifact_id": trace.artifact_id,
                    "evidence_packet_artifact_id": evidence_packet.artifact_id,
                    "evidence_artifact_id": evidence.artifact_id,
                    "locator_artifact_id": evidence.locator.artifact_id,
                    "source_artifact_id": evidence.locator.source_artifact_id,
                    "source_content_sha256": evidence.locator.source_content_sha256,
                    "exact_text_sha256": evidence.exact_text_sha256,
                    "relation": relation.relation.value,
                }
                path = EvidenceProvenancePath(
                    artifact_id=content_artifact_id(payload),
                    synthesized_claim_artifact_id=claim.artifact_id,
                    canonical_claim_artifact_id=claim.canonical_claim_artifact_id,
                    source_claim_artifact_id=relation.claim_artifact_id,
                    evidence_relation_artifact_id=relation.artifact_id,
                    relation_trace_artifact_id=trace.artifact_id,
                    evidence_packet_artifact_id=evidence_packet.artifact_id,
                    evidence_artifact_id=evidence.artifact_id,
                    locator_artifact_id=evidence.locator.artifact_id,
                    source_artifact_id=evidence.locator.source_artifact_id,
                    source_content_sha256=evidence.locator.source_content_sha256,
                    exact_text_sha256=evidence.exact_text_sha256,
                    relation=relation.relation,
                )
                paths.append(path)
                claim_paths.append(path)
            ordered_path_ids = tuple(sorted(item.artifact_id for item in claim_paths))
            counts = Counter(item.relation for item in claim_paths)
            resolution_payload = {
                "synthesized_claim_artifact_id": claim.artifact_id,
                "canonical_claim_artifact_id": claim.canonical_claim_artifact_id,
                "evidence_path_artifact_ids": ordered_path_ids,
                "support_path_count": counts[EvidenceRelationKind.supports],
                "opposition_path_count": counts[EvidenceRelationKind.opposes],
                "ambiguous_path_count": counts[EvidenceRelationKind.ambiguous],
            }
            resolutions.append(
                ClaimProvenanceResolution(
                    artifact_id=content_artifact_id(resolution_payload),
                    synthesized_claim_artifact_id=claim.artifact_id,
                    canonical_claim_artifact_id=claim.canonical_claim_artifact_id,
                    evidence_path_artifact_ids=ordered_path_ids,
                    support_path_count=counts[EvidenceRelationKind.supports],
                    opposition_path_count=counts[EvidenceRelationKind.opposes],
                    ambiguous_path_count=counts[EvidenceRelationKind.ambiguous],
                )
            )
        ordered_paths = tuple(sorted(paths, key=lambda item: item.artifact_id))
        ordered_resolutions = tuple(
            sorted(resolutions, key=lambda item: item.synthesized_claim_artifact_id)
        )
        self._verify_content_identities(
            synthesis,
            evidence_packet,
            claim_merge,
            evidence_relations,
            assumption_insufficiency,
            convergence,
        )
        verified_evidence_ids = tuple(
            sorted({item.evidence_artifact_id for item in ordered_paths})
        )
        payload = {
            "schema_version": "bijux.canon.reason.reasoning_provenance_report.v1",
            "synthesis_artifact_id": synthesis.artifact_id,
            "graph_artifact_id": synthesis.graph_artifact_id,
            "evidence_packet_artifact_id": evidence_packet.artifact_id,
            "claim_merge_artifact_id": claim_merge.artifact_id,
            "evidence_relation_attachment_artifact_id": evidence_relations.artifact_id,
            "assumption_insufficiency_artifact_id": assumption_insufficiency.artifact_id,
            "convergence_decision_artifact_id": convergence.artifact_id,
            "evidence_paths": tuple(
                item.model_dump(mode="json") for item in ordered_paths
            ),
            "claim_resolutions": tuple(
                item.model_dump(mode="json") for item in ordered_resolutions
            ),
            "verified_evidence_artifact_ids": verified_evidence_ids,
            "synthesis_outcome": synthesis.outcome.value,
        }
        return ReasoningProvenanceReport(
            artifact_id=content_artifact_id(payload),
            synthesis_artifact_id=synthesis.artifact_id,
            graph_artifact_id=synthesis.graph_artifact_id,
            evidence_packet_artifact_id=evidence_packet.artifact_id,
            claim_merge_artifact_id=claim_merge.artifact_id,
            evidence_relation_attachment_artifact_id=evidence_relations.artifact_id,
            assumption_insufficiency_artifact_id=assumption_insufficiency.artifact_id,
            convergence_decision_artifact_id=convergence.artifact_id,
            evidence_paths=ordered_paths,
            claim_resolutions=ordered_resolutions,
            verified_evidence_artifact_ids=verified_evidence_ids,
            synthesis_outcome=synthesis.outcome,
        )

    @staticmethod
    def _verify_source_links(
        synthesis: VerifiedGraphSynthesis,
        claim_merge: ClaimMergeResult,
        relations: EvidenceRelationAttachment,
        insufficiency: AssumptionInsufficiencyDelta,
        convergence: ConvergenceDecision,
    ) -> None:
        observed = (
            synthesis.claim_merge_artifact_id,
            synthesis.evidence_relation_attachment_artifact_id,
            synthesis.assumption_insufficiency_artifact_id,
            synthesis.convergence_decision_artifact_id,
        )
        expected = (
            claim_merge.artifact_id,
            relations.artifact_id,
            insufficiency.artifact_id,
            convergence.artifact_id,
        )
        if observed != expected:
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.source_identity_mismatch,
                "synthesis source identities do not match supplied graph products",
            )

    @staticmethod
    def _verify_graph_identities(
        synthesis: VerifiedGraphSynthesis,
        claim_merge: ClaimMergeResult,
        relations: EvidenceRelationAttachment,
        insufficiency: AssumptionInsufficiencyDelta,
        convergence: ConvergenceDecision,
    ) -> None:
        graph_ids = {
            synthesis.graph_artifact_id,
            claim_merge.graph_artifact_id,
            relations.graph_artifact_id,
            insufficiency.graph_artifact_id,
            convergence.current_graph_artifact_id,
        }
        if len(graph_ids) != 1:
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.graph_identity_mismatch,
                "provenance inputs do not describe one exact graph",
            )

    @staticmethod
    def _verify_evidence(
        evidence_packet: EvidencePacket,
    ) -> dict[str, CitationEvidence]:
        evidence_by_id: dict[str, CitationEvidence] = {}
        for evidence in evidence_packet.selected:
            if evidence.artifact_id in evidence_by_id:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.unadmitted_evidence,
                    "admitted evidence identities must be unique",
                )
            exact_digest = hashlib.sha256(evidence.exact_text.encode("utf-8")).hexdigest()
            if exact_digest != evidence.exact_text_sha256:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.digest_mismatch,
                    "exact evidence text does not match its admitted digest",
                )
            if evidence.locator.source_artifact_id != (
                f"sha256:{evidence.locator.source_content_sha256}"
            ):
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.digest_mismatch,
                    "source artifact identity does not match its content digest",
                )
            evidence_by_id[evidence.artifact_id] = evidence
        return evidence_by_id

    @staticmethod
    def _verify_dependencies(
        claim_merge: ClaimMergeResult, canonical_ids: set[str]
    ) -> None:
        children = {item: set() for item in canonical_ids}
        indegree = {item: 0 for item in canonical_ids}
        for dependency in claim_merge.dependencies:
            parent = dependency.parent_canonical_claim_artifact_id
            child = dependency.child_canonical_claim_artifact_id
            if parent not in canonical_ids or child not in canonical_ids:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.orphan_claim,
                    "a derivation dependency references an unknown canonical claim",
                )
            if dependency.internal_to_canonical_claim:
                continue
            if child not in children[parent]:
                children[parent].add(child)
                indegree[child] += 1
        ready = sorted(item for item, degree in indegree.items() if degree == 0)
        visited = 0
        while ready:
            node = ready.pop(0)
            visited += 1
            for child in sorted(children[node]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()
        if visited != len(canonical_ids):
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.dependency_cycle,
                "canonical derivation dependencies contain a cycle",
            )

    @staticmethod
    def _verify_claim_edges(
        claim: SynthesizedGraphClaim, relations: tuple[GraphEvidenceRelation, ...]
    ) -> None:
        relation_ids = tuple(sorted(item.artifact_id for item in relations))
        evidence_ids = tuple(sorted({item.evidence_artifact_id for item in relations}))
        support_count = sum(
            item.relation is EvidenceRelationKind.supports for item in relations
        )
        if (
            support_count == 0
            or claim.evidence_relation_artifact_ids != relation_ids
            or claim.evidence_artifact_ids != evidence_ids
        ):
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.orphan_claim,
                "a final claim does not resolve through its exact evidence relations",
            )

    @staticmethod
    def _verify_confidence(
        claim: SynthesizedGraphClaim,
        relations: tuple[GraphEvidenceRelation, ...],
        synthesis: VerifiedGraphSynthesis,
        insufficiency: AssumptionInsufficiencyDelta,
        resolve: Callable[[str], str],
    ) -> None:
        evidence = {
            kind: tuple(
                sorted(
                    {
                        item.evidence_artifact_id
                        for item in relations
                        if item.relation is kind
                    }
                )
            )
            for kind in EvidenceRelationKind
        }
        conflict_sources = {
            source_id
            for conflict in synthesis.conflicts
            if claim.canonical_claim_artifact_id
            in conflict.canonical_claim_artifact_ids
            for source_id in conflict.source_artifact_ids
        }
        relation_ids = {item.artifact_id for item in relations}
        declared_conflicts = tuple(sorted(conflict_sources - relation_ids))
        assumptions = tuple(
            sorted(
                item.artifact_id
                for item in insufficiency.assumptions
                if resolve(item.claim_artifact_id)
                == claim.canonical_claim_artifact_id
                and item.status is not AssumptionStatus.tested
            )
        )
        open_statuses = {
            ResearchDeficiencyStatus.open,
            ResearchDeficiencyStatus.searching,
            ResearchDeficiencyStatus.unresolved,
        }
        deficiencies = tuple(
            sorted(
                item.artifact_id
                for item in insufficiency.deficiencies
                if item.status in open_statuses
                and (
                    item.target_claim_artifact_id is None
                    or resolve(item.target_claim_artifact_id)
                    == claim.canonical_claim_artifact_id
                )
            )
        )
        inputs = (
            evidence[EvidenceRelationKind.supports],
            evidence[EvidenceRelationKind.opposes],
            evidence[EvidenceRelationKind.ambiguous],
            declared_conflicts,
            assumptions,
            deficiencies,
        )
        denominator = sum(len(item) for item in inputs)
        score = round(len(inputs[0]) / denominator, 6) if denominator else 0.0
        level = _confidence_level(score)
        basis = claim.confidence
        observed = (
            basis.support_evidence_artifact_ids,
            basis.opposition_evidence_artifact_ids,
            basis.ambiguous_evidence_artifact_ids,
            basis.declared_conflict_artifact_ids,
            basis.material_assumption_artifact_ids,
            basis.open_deficiency_artifact_ids,
            basis.score,
            basis.level,
        )
        expected = (*inputs, score, level)
        if observed != expected:
            raise ReasoningProvenanceError(
                ReasoningProvenanceErrorCode.unsupported_confidence,
                "claim confidence is not supported by exact graph state",
            )

    @staticmethod
    def _verify_content_identities(*artifacts: StableModel) -> None:
        for artifact in artifacts:
            expected = content_artifact_id(
                artifact.model_dump(mode="json", exclude={"artifact_id"})
            )
            if getattr(artifact, "artifact_id", None) != expected:
                raise ReasoningProvenanceError(
                    ReasoningProvenanceErrorCode.artifact_identity_mismatch,
                    f"artifact identity mismatch for {type(artifact).__name__}",
                )


def _confidence_level(score: float) -> SynthesisConfidenceLevel:
    if score == 0:
        return SynthesisConfidenceLevel.unsupported
    if score < 0.5:
        return SynthesisConfidenceLevel.low
    if score < 0.8:
        return SynthesisConfidenceLevel.moderate
    return SynthesisConfidenceLevel.high


__all__ = [
    "ClaimProvenanceResolution",
    "EvidenceProvenancePath",
    "ReasoningProvenanceError",
    "ReasoningProvenanceErrorCode",
    "ReasoningProvenanceReport",
    "ReasoningProvenanceVerifier",
]
