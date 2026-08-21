# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Scoped research-gap retrieval orchestration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_reason.research import (
    EvidenceChange,
    GapRetrievalError,
    GapRetrievalErrorCode,
    GapRetrievalPolicy,
    GapRetrievalService,
    QuestionDecomposer,
    ResearchQuestion,
    RetrievalBatchStatus,
    SubquestionStatus,
    create_retrieval_evidence_batch,
    create_subquestion_candidate,
    create_subquestion_retrieval_request,
)

_REPO = Path(__file__).resolve().parents[5]


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _subquestion(
    text: str = "Which exact source sentence defines FASTQ?", *, priority: int = 90
):
    records = json.loads(
        (
            _REPO / "apis/bijux-canon-reason/v2/examples/evaluation-claim-records.json"
        ).read_text()
    )["records"]
    question = ResearchQuestion.model_validate(
        next(
            item
            for item in records
            if item["artifact_type"] == "bijux.canon.reason.question"
        )
    )
    candidate = create_subquestion_candidate(
        text=text,
        scope_artifact_id=question.scope_artifact_id,
        rationale="This query resolves a declared evidence need.",
        evidence_needs=("exact source span", "support relation"),
        priority=priority,
    )
    return QuestionDecomposer().decompose(question, (candidate,)).subquestions[0]


class _Port:
    def __init__(
        self,
        evidence: tuple[str, ...],
        status: RetrievalBatchStatus = RetrievalBatchStatus.success,
        refusal_code: str | None = None,
    ) -> None:
        self.evidence = evidence
        self.status = status
        self.refusal_code = refusal_code
        self.calls = []

    def retrieve(self, request):
        self.calls.append(request.artifact_id)
        return create_retrieval_evidence_batch(
            request,
            retrieval_trace_artifact_id=_artifact("a"),
            generation_artifact_id=_artifact("b"),
            status=self.status,
            evidence_artifact_ids=self.evidence,
            refusal_code=self.refusal_code,
        )


def test_retrieval_records_new_and_repeated_evidence_exactly() -> None:
    known = _artifact("1")
    added = _artifact("2")
    request = create_subquestion_retrieval_request(
        _subquestion(),
        graph_artifact_id=_artifact("3"),
        prior_evidence_artifact_ids=(known,),
        top_k=2,
    )
    port = _Port((known, added))

    result = GapRetrievalService().retrieve((request,), port)

    assert port.calls == [request.artifact_id]
    assert result.request_artifact_ids == (request.artifact_id,)
    assert result.records[0].change is EvidenceChange.evidence_added
    assert result.records[0].added_evidence_artifact_ids == (added,)
    assert result.records[0].repeated_evidence_artifact_ids == (known,)
    assert request.rationale == "This query resolves a declared evidence need."


@pytest.mark.parametrize(
    ("status", "refusal_code", "expected"),
    [
        (RetrievalBatchStatus.no_matches, None, EvidenceChange.no_new_evidence),
        (
            RetrievalBatchStatus.refused,
            "scope_denied",
            EvidenceChange.retrieval_refused,
        ),
    ],
)
def test_empty_and_refused_results_remain_typed(status, refusal_code, expected) -> None:
    request = create_subquestion_retrieval_request(
        _subquestion(), graph_artifact_id=_artifact("3")
    )

    result = GapRetrievalService().retrieve(
        (request,), _Port((), status=status, refusal_code=refusal_code)
    )

    assert result.records[0].change is expected
    assert result.records[0].added_evidence_artifact_ids == ()


def test_priority_order_is_deterministic() -> None:
    high = create_subquestion_retrieval_request(
        _subquestion("Which exact source sentence defines FASTQ?"),
        graph_artifact_id=_artifact("3"),
    )
    low_subquestion = _subquestion(
        "How is each FASTQ record structured into lines?", priority=20
    )
    low = create_subquestion_retrieval_request(
        low_subquestion, graph_artifact_id=_artifact("3")
    )
    port = _Port((_artifact("4"),))

    result = GapRetrievalService().retrieve((low, high), port)

    assert result.request_artifact_ids == (high.artifact_id, low.artifact_id)
    assert port.calls == [high.artifact_id, low.artifact_id]


def test_adapter_identity_mismatch_fails_closed() -> None:
    request = create_subquestion_retrieval_request(
        _subquestion(), graph_artifact_id=_artifact("3")
    )

    class MismatchedPort(_Port):
        def retrieve(self, value):
            batch = super().retrieve(value)
            return batch.model_copy(update={"query_text_sha256": "0" * 64})

    with pytest.raises(GapRetrievalError) as caught:
        GapRetrievalService().retrieve((request,), MismatchedPort((_artifact("4"),)))

    assert caught.value.code is GapRetrievalErrorCode.query_identity_mismatch


def test_request_and_result_budgets_fail_closed() -> None:
    request = create_subquestion_retrieval_request(
        _subquestion(), graph_artifact_id=_artifact("3"), top_k=1
    )
    service = GapRetrievalService(
        GapRetrievalPolicy(max_requests=1, max_evidence_per_request=1)
    )

    with pytest.raises(GapRetrievalError) as caught:
        service.retrieve((request,), _Port((_artifact("4"), _artifact("5"))))
    assert caught.value.code is GapRetrievalErrorCode.result_limit_exceeded

    with pytest.raises(GapRetrievalError) as duplicate:
        service.retrieve((request, request), _Port((_artifact("4"),)))
    assert duplicate.value.code is GapRetrievalErrorCode.request_budget_exceeded


def test_answered_subquestion_cannot_open_an_unresolved_request() -> None:
    answered = _subquestion().model_copy(update={"status": SubquestionStatus.answered})

    with pytest.raises(GapRetrievalError) as caught:
        create_subquestion_retrieval_request(answered, graph_artifact_id=_artifact("3"))

    assert caught.value.code is GapRetrievalErrorCode.target_resolved
