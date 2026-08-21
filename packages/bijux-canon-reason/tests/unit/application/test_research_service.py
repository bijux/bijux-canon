# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application-level persistence and parity tests for bounded research."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_reason.application import (
    ResearchApplicationError,
    ResearchApplicationErrorCode,
    ResearchApplicationInput,
    ResearchApplicationService,
)
from bijux_canon_reason.grounding import EvidencePacketBuilder, EvidencePacketPolicy
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    AssumptionInsufficiencyDelta,
    ClaimMergingService,
    ConvergenceService,
    EvidenceRelationAttachment,
    ResearchSynthesisOutcome,
    create_convergence_observation,
)


def _id(name: str) -> str:
    return content_artifact_id({"name": name})


def _request() -> ResearchApplicationInput:
    graph_id = _id("application-graph")
    merge = ClaimMergingService().merge(graph_artifact_id=graph_id, claims=())
    attachment_payload = {
        "schema_version": "bijux.canon.reason.evidence_relation_attachment.v1",
        "graph_artifact_id": graph_id,
        "verification_report_artifact_id": _id("verification-report"),
        "relations": (),
        "traces": (),
        "rejected": (),
    }
    attachment = EvidenceRelationAttachment(
        artifact_id=content_artifact_id(attachment_payload), **attachment_payload
    )
    delta_payload = {
        "schema_version": "bijux.canon.reason.assumption_insufficiency_delta.v1",
        "graph_artifact_id": graph_id,
        "relation_attachment_artifact_id": attachment.artifact_id,
        "assumptions": (),
        "insufficiencies": (),
        "deficiencies": (),
    }
    delta = AssumptionInsufficiencyDelta(
        artifact_id=content_artifact_id(delta_payload), **delta_payload
    )
    convergence = ConvergenceService().evaluate(
        (
            create_convergence_observation(
                iteration=1,
                graph_artifact_id=graph_id,
                coverage=0.0,
                verified_answerable_claims=0,
                required_claims=1,
                blocking_gap_count=1,
                new_evidence_count=0,
                marginal_evidence_value=0.0,
                cumulative_tool_calls=0,
                cumulative_tokens=0,
                cumulative_elapsed_ms=1,
                explicit_insufficiency=True,
            ),
        )
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=10,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_id("question"),
        scope_artifact_id=_id("scope"),
        retrieval_trace_artifact_ids=(_id("retrieval-trace"),),
        candidates=(),
    )
    return ResearchApplicationInput(
        question="What can the admitted evidence establish?",
        evidence_packet=packet,
        claim_merge=merge,
        evidence_relations=attachment,
        assumption_insufficiency=delta,
        convergence=convergence,
    )


def test_all_research_operations_share_one_restart_safe_record(tmp_path: Path) -> None:
    service = ResearchApplicationService(artifacts_dir=tmp_path)
    record = service.research(_request())

    assert record.synthesis.outcome is ResearchSynthesisOutcome.insufficient
    assert service.inspect(record.research_id) == record
    assert service.verify(record.research_id).passed
    assert service.replay(record.research_id) == record.replayed_attempts
    assert service.compare(record.research_id) == record.comparison
    assert record.comparison.removed_decision_artifact_ids == (
        record.synthesis.artifact_id,
    )
    assert record.comparison.added_decision_artifact_ids == (
        record.provenance.artifact_id,
    )


def test_research_inspection_rejects_manifested_record_tampering(
    tmp_path: Path,
) -> None:
    service = ResearchApplicationService(artifacts_dir=tmp_path)
    record = service.research(_request())
    path = tmp_path / "research" / record.research_id / "research.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["request"]["question"] = "Tampered question"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ResearchApplicationError) as error:
        service.inspect(record.research_id)

    assert error.value.code is ResearchApplicationErrorCode.integrity_mismatch


def test_research_service_rejects_noncanonical_identity(tmp_path: Path) -> None:
    service = ResearchApplicationService(artifacts_dir=tmp_path)

    with pytest.raises(ResearchApplicationError) as error:
        service.inspect("../another-run")

    assert error.value.code is ResearchApplicationErrorCode.invalid_research_id
