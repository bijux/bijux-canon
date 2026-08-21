# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Restart-safe application service for bounded research operations."""

from __future__ import annotations

from enum import StrEnum
import hashlib
from pathlib import Path
import re
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding import (
    ClaimConflictDeclaration,
    ClaimContextAnnotation,
    EvidencePacket,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.interfaces.serialization.json_file import (
    read_json_file,
    write_json_file,
)
from bijux_canon_reason.research import (
    AssumptionInsufficiencyDelta,
    ClaimMergeResult,
    ConvergenceDecision,
    EvidenceRelationAttachment,
    ReasoningProvenanceReport,
    ReasoningProvenanceVerifier,
    ReplayedResearchAttempt,
    ResearchAttemptComparison,
    ResearchChangeAuthority,
    ResearchGraphEvent,
    ResearchGraphEventKind,
    ResearchReasoningAttempt,
    ResearchReasoningReplayService,
    VerifiedGraphSynthesis,
    VerifiedGraphSynthesisService,
    create_research_graph_event,
    create_research_reasoning_attempt,
)


class ResearchApplicationErrorCode(StrEnum):
    """Stable failures at the persisted research application boundary."""

    not_found = "not_found"
    invalid_research_id = "invalid_research_id"
    integrity_mismatch = "integrity_mismatch"
    replay_mismatch = "replay_mismatch"


class ResearchApplicationError(ValueError):
    """A persisted research operation cannot be completed safely."""

    def __init__(self, code: ResearchApplicationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ResearchApplicationInput(StableModel):
    """Complete verified-graph input required to execute bounded RAR."""

    schema_version: Literal["bijux.canon.reason.research_application_input.v1"] = (
        "bijux.canon.reason.research_application_input.v1"
    )
    question: str
    evidence_packet: EvidencePacket
    claim_merge: ClaimMergeResult
    evidence_relations: EvidenceRelationAttachment
    assumption_insufficiency: AssumptionInsufficiencyDelta
    convergence: ConvergenceDecision
    contexts: tuple[ClaimContextAnnotation, ...] = ()
    declared_conflicts: tuple[ClaimConflictDeclaration, ...] = ()

    @field_validator("question")
    @classmethod
    def _question_required(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("research question must not be empty")
        return normalized


class ResearchApplicationRecord(StableModel):
    """Complete persisted output shared by inspect, verify, replay, and compare."""

    schema_version: Literal["bijux.canon.reason.research_application_record.v1"] = (
        "bijux.canon.reason.research_application_record.v1"
    )
    artifact_id: str
    research_id: str
    request: ResearchApplicationInput
    synthesis: VerifiedGraphSynthesis
    provenance: ReasoningProvenanceReport
    attempts: tuple[ResearchReasoningAttempt, ResearchReasoningAttempt]
    replayed_attempts: tuple[ReplayedResearchAttempt, ReplayedResearchAttempt]
    comparison: ResearchAttemptComparison

    @field_validator("artifact_id")
    @classmethod
    def _artifact_identity(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_record(self) -> Self:
        expected_research_id = stable_id(
            "research", self.request.model_dump(mode="json")
        )
        if self.research_id != expected_research_id:
            raise ValueError("research identity does not match its immutable input")
        expected_artifact_id = content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        )
        if self.artifact_id != expected_artifact_id:
            raise ValueError("research record identity does not match its content")
        if self.comparison.baseline_attempt_artifact_id != self.attempts[0].artifact_id:
            raise ValueError("comparison baseline does not match the root attempt")
        if self.comparison.current_attempt_artifact_id != self.attempts[1].artifact_id:
            raise ValueError("comparison current attempt does not match the child attempt")
        return self


class ResearchApplicationVerification(StableModel):
    """Exact restart verification of one persisted research record."""

    schema_version: Literal[
        "bijux.canon.reason.research_application_verification.v1"
    ] = "bijux.canon.reason.research_application_verification.v1"
    artifact_id: str
    research_id: str
    record_artifact_id: str
    synthesis_exact: bool
    provenance_exact: bool
    replay_exact: bool
    comparison_exact: bool
    passed: bool

    @field_validator("artifact_id", "record_artifact_id")
    @classmethod
    def _artifact_identity(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_verification(self) -> Self:
        checks = (
            self.synthesis_exact,
            self.provenance_exact,
            self.replay_exact,
            self.comparison_exact,
        )
        if self.passed != all(checks):
            raise ValueError("verification outcome does not match exact checks")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research verification identity does not match")
        return self


class ResearchApplicationService:
    """Own research execution, persistence, inspection, verification, and replay."""

    def __init__(self, *, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir
        self._replay = ResearchReasoningReplayService()

    def research(self, request: ResearchApplicationInput) -> ResearchApplicationRecord:
        """Execute the verified graph and persist one immutable research record."""
        record = self._build_record(request)
        research_dir = self._research_dir(record.research_id)
        record_path = research_dir / "research.json"
        write_json_file(record_path, record.model_dump(mode="json"))
        write_json_file(
            research_dir / "manifest.json",
            {
                "schema_version": "bijux.canon.reason.research_manifest.v1",
                "research_id": record.research_id,
                "files": {"research.json": _sha256(record_path)},
            },
        )
        return record

    def inspect(self, research_id: str) -> ResearchApplicationRecord:
        """Load and validate the complete persisted research record."""
        return self._load_record(research_id)

    def verify(self, research_id: str) -> ResearchApplicationVerification:
        """Recompute synthesis, provenance, replay, and comparison after restart."""
        record = self._load_record(research_id)
        expected = self._build_record(record.request)
        checks = {
            "synthesis_exact": expected.synthesis == record.synthesis,
            "provenance_exact": expected.provenance == record.provenance,
            "replay_exact": expected.replayed_attempts == record.replayed_attempts,
            "comparison_exact": expected.comparison == record.comparison,
        }
        passed = all(checks.values())
        payload = {
            "schema_version": (
                "bijux.canon.reason.research_application_verification.v1"
            ),
            "research_id": research_id,
            "record_artifact_id": record.artifact_id,
            **checks,
            "passed": passed,
        }
        return ResearchApplicationVerification(
            artifact_id=content_artifact_id(payload),
            research_id=research_id,
            record_artifact_id=record.artifact_id,
            synthesis_exact=checks["synthesis_exact"],
            provenance_exact=checks["provenance_exact"],
            replay_exact=checks["replay_exact"],
            comparison_exact=checks["comparison_exact"],
            passed=passed,
        )

    def replay(
        self, research_id: str
    ) -> tuple[ReplayedResearchAttempt, ReplayedResearchAttempt]:
        """Replay the immutable attempt chain and require exact persisted parity."""
        record = self._load_record(research_id)
        replayed = self._replay.replay_chain(record.attempts)
        if replayed != record.replayed_attempts:
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.replay_mismatch,
                "replayed research state differs from the persisted state",
            )
        return replayed

    def compare(self, research_id: str) -> ResearchAttemptComparison:
        """Compare the root and child attempt with exact event attribution."""
        record = self._load_record(research_id)
        replayed = self.replay(research_id)
        comparison = self._replay.compare(
            baseline=replayed[0],
            current=replayed[1],
            current_attempt=record.attempts[1],
        )
        if comparison != record.comparison:
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.replay_mismatch,
                "research comparison differs from the persisted comparison",
            )
        return comparison

    def _build_record(
        self, request: ResearchApplicationInput
    ) -> ResearchApplicationRecord:
        synthesis = VerifiedGraphSynthesisService().synthesize(
            question=request.question,
            claim_merge=request.claim_merge,
            evidence_relations=request.evidence_relations,
            assumption_insufficiency=request.assumption_insufficiency,
            convergence=request.convergence,
            contexts=request.contexts,
            declared_conflicts=request.declared_conflicts,
        )
        provenance = ReasoningProvenanceVerifier().verify(
            synthesis=synthesis,
            evidence_packet=request.evidence_packet,
            claim_merge=request.claim_merge,
            evidence_relations=request.evidence_relations,
            assumption_insufficiency=request.assumption_insufficiency,
            convergence=request.convergence,
        )
        attempts, replayed, comparison = self._attempt_history(
            request=request,
            synthesis=synthesis,
            provenance=provenance,
        )
        research_id = stable_id("research", request.model_dump(mode="json"))
        payload = {
            "schema_version": "bijux.canon.reason.research_application_record.v1",
            "research_id": research_id,
            "request": request.model_dump(mode="json"),
            "synthesis": synthesis.model_dump(mode="json"),
            "provenance": provenance.model_dump(mode="json"),
            "attempts": tuple(item.model_dump(mode="json") for item in attempts),
            "replayed_attempts": tuple(
                item.model_dump(mode="json") for item in replayed
            ),
            "comparison": comparison.model_dump(mode="json"),
        }
        return ResearchApplicationRecord(
            artifact_id=content_artifact_id(payload),
            research_id=research_id,
            request=request,
            synthesis=synthesis,
            provenance=provenance,
            attempts=attempts,
            replayed_attempts=replayed,
            comparison=comparison,
        )

    def _attempt_history(
        self,
        *,
        request: ResearchApplicationInput,
        synthesis: VerifiedGraphSynthesis,
        provenance: ReasoningProvenanceReport,
    ) -> tuple[
        tuple[ResearchReasoningAttempt, ResearchReasoningAttempt],
        tuple[ReplayedResearchAttempt, ReplayedResearchAttempt],
        ResearchAttemptComparison,
    ]:
        input_ids = tuple(
            sorted(
                {
                    request.evidence_packet.artifact_id,
                    request.claim_merge.artifact_id,
                    request.evidence_relations.artifact_id,
                    request.assumption_insufficiency.artifact_id,
                    request.convergence.artifact_id,
                    *(item.artifact_id for item in request.contexts),
                    *(item.artifact_id for item in request.declared_conflicts),
                }
            )
        )
        root_events = _events(
            tuple(
                (ResearchGraphEventKind.claim_admitted, item.artifact_id)
                for item in synthesis.consensus + synthesis.conflicted_claims
            )
            + tuple(
                (ResearchGraphEventKind.evidence_admitted, evidence_id)
                for evidence_id in provenance.verified_evidence_artifact_ids
            )
            + ((ResearchGraphEventKind.decision_recorded, synthesis.artifact_id),),
            authority_artifact_id=request.convergence.artifact_id,
        )
        root = create_research_reasoning_attempt(
            research_input_artifact_ids=input_ids,
            events=root_events,
        )
        root_replay = self._replay.replay_chain((root,))[0]
        child_events = _events(
            (
                (
                    ResearchGraphEventKind.decision_superseded,
                    synthesis.artifact_id,
                ),
                (ResearchGraphEventKind.decision_recorded, provenance.artifact_id),
            ),
            authority_artifact_id=provenance.artifact_id,
        )
        child = create_research_reasoning_attempt(
            research_input_artifact_ids=tuple(sorted((*input_ids, provenance.artifact_id))),
            events=child_events,
            parent_attempt_artifact_id=root.artifact_id,
            base_state_artifact_id=root_replay.state_artifact_id,
        )
        attempts = (root, child)
        replayed_chain = self._replay.replay_chain(attempts)
        replayed = (replayed_chain[0], replayed_chain[1])
        comparison = self._replay.compare(
            baseline=replayed[0],
            current=replayed[1],
            current_attempt=child,
        )
        return attempts, replayed, comparison

    def _load_record(self, research_id: str) -> ResearchApplicationRecord:
        research_dir = self._research_dir(research_id)
        record_path = research_dir / "research.json"
        manifest_path = research_dir / "manifest.json"
        if not record_path.exists() or not manifest_path.exists():
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.not_found,
                "research record or manifest not found",
            )
        manifest = read_json_file(manifest_path)
        if not isinstance(manifest, dict):
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.integrity_mismatch,
                "research manifest is not a JSON object",
            )
        files = manifest.get("files")
        expected = files.get("research.json") if isinstance(files, dict) else None
        if (
            manifest.get("research_id") != research_id
            or not isinstance(expected, str)
            or expected != _sha256(record_path)
        ):
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.integrity_mismatch,
                "research record digest does not match its manifest",
            )
        return ResearchApplicationRecord.model_validate(read_json_file(record_path))

    def _research_dir(self, research_id: str) -> Path:
        if not re.fullmatch(r"research_v1_[0-9a-f]{64}", research_id):
            raise ResearchApplicationError(
                ResearchApplicationErrorCode.invalid_research_id,
                "research id is not a canonical content identity",
            )
        return self._artifacts_dir / "research" / research_id


def _events(
    kinds_and_targets: tuple[tuple[ResearchGraphEventKind, str], ...],
    *,
    authority_artifact_id: str,
) -> tuple[ResearchGraphEvent, ...]:
    events: list[ResearchGraphEvent] = []
    for sequence, (kind, target) in enumerate(kinds_and_targets, start=1):
        events.append(
            create_research_graph_event(
                sequence=sequence,
                previous_event_artifact_id=(
                    events[-1].artifact_id if events else None
                ),
                kind=kind,
                target_artifact_id=target,
                authority=ResearchChangeAuthority.deterministic,
                authority_provenance_artifact_id=authority_artifact_id,
            )
        )
    return tuple(events)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "ResearchApplicationError",
    "ResearchApplicationErrorCode",
    "ResearchApplicationInput",
    "ResearchApplicationRecord",
    "ResearchApplicationService",
    "ResearchApplicationVerification",
]
