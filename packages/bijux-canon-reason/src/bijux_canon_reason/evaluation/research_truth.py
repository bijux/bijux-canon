# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Adapt reviewed semantic research questions into executable evaluation truth."""

from __future__ import annotations

from datetime import date
import hashlib
from typing import Mapping

from bijux_canon_reason.evaluation.truth import (
    AbstentionExpectation,
    AtomicClaimTruth,
    CitationTruthLabel,
    CitationTruthRelation,
    ClaimTruthClass,
    ConflictExpectation,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationSplit,
    ExactEvidenceLocator,
    QrelJudgment,
    TruthProvenance,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id


class ResearchTruthAdaptationError(ValueError):
    """Reviewed question, claim, qrel, or source bindings are incomplete."""


class ResearchQuestionTruthAdapter:
    """Build Reason-owned truth without consulting a system output."""

    def adapt_development(
        self,
        *,
        cases: tuple[Mapping[str, object], ...],
        question_claims: tuple[Mapping[str, object], ...],
        qrels: tuple[Mapping[str, object], ...],
        source_uris: Mapping[str, str],
    ) -> tuple[EvaluationCaseTruth, ...]:
        """Return every visible development case as typed immutable truth."""

        cases_by_id = {_string(item, "case_id"): item for item in cases}
        qrels_by_id = {_string(item, "qrel_id"): item for item in qrels}
        if len(cases_by_id) != len(cases) or len(qrels_by_id) != len(qrels):
            raise ResearchTruthAdaptationError("research truth identities must be unique")
        results = tuple(
            self._case(
                raw_claims,
                cases_by_id=cases_by_id,
                qrels_by_id=qrels_by_id,
                source_uris=source_uris,
            )
            for raw_claims in sorted(
                question_claims,
                key=lambda item: _string(item, "case_id"),
            )
        )
        expected_case_ids = {
            case_id
            for case_id, item in cases_by_id.items()
            if item.get("split") == "development"
        }
        if {item.case_id for item in results} != expected_case_ids:
            raise ResearchTruthAdaptationError(
                "question-claim truth does not cover the development population"
            )
        return results

    def _case(
        self,
        raw_claims: Mapping[str, object],
        *,
        cases_by_id: Mapping[str, Mapping[str, object]],
        qrels_by_id: Mapping[str, Mapping[str, object]],
        source_uris: Mapping[str, str],
    ) -> EvaluationCaseTruth:
        case_id = _string(raw_claims, "case_id")
        raw_case = cases_by_id.get(case_id)
        if raw_case is None or raw_case.get("split") != "development":
            raise ResearchTruthAdaptationError(
                f"question-claim truth names a non-development case: {case_id}"
            )
        if (
            raw_claims.get("schema_version")
            != "bijux.canon.research_question_claim_truth.v1"
            or raw_claims.get("system_output_consulted") is not False
            or raw_case.get("system_output_may_define_truth") is not False
        ):
            raise ResearchTruthAdaptationError(
                "research truth must remain independent of system output"
            )
        question_id = _string(raw_claims, "question_id")
        if question_id != _string(raw_case, "question_id"):
            raise ResearchTruthAdaptationError("question-claim case binding differs")
        raw_truth = _mapping(raw_case, "truth")
        raw_points = _values(raw_truth, "acceptable_answer_points")
        raw_claim_rows = _mapping_sequence(raw_claims, "claims")
        if tuple(_string(item, "statement") for item in raw_claim_rows) != tuple(
            str(item) for item in raw_points
        ):
            raise ResearchTruthAdaptationError(
                "question-claim statements differ from reviewed answer points"
            )
        question_evidence = {
            _string(item, "qrel_id"): item
            for item in _mapping_sequence(raw_truth, "evidence")
        }
        cited_qrel_ids = {
            _string(citation, "qrel_id")
            for claim in raw_claim_rows
            for citation in _mapping_sequence(claim, "citations")
        }
        if not cited_qrel_ids.issubset(question_evidence):
            raise ResearchTruthAdaptationError(
                "question claim names evidence outside reviewed question truth"
            )
        qrel_models = tuple(
            self._qrel(
                qrels_by_id[qrel_id],
                question_id=question_id,
                rationale=_string(question_evidence[qrel_id], "rationale"),
                relevance_grade=_integer(
                    question_evidence[qrel_id], "relevance_grade"
                ),
                source_uris=source_uris,
            )
            for qrel_id in sorted(cited_qrel_ids)
            if qrel_id in qrels_by_id
        )
        if len(qrel_models) != len(cited_qrel_ids):
            raise ResearchTruthAdaptationError("question claim names an unknown qrel")
        claim_models = tuple(
            self._claim(
                item,
                index=index,
                case_id=case_id,
                question_id=question_id,
                qrels_by_id=qrels_by_id,
                raw_claims=raw_claims,
            )
            for index, item in enumerate(raw_claim_rows)
        )
        case_provenance = _provenance(
            reviewer_id=_string(raw_truth, "reviewer_id"),
            reviewed_on=_string(raw_truth, "reviewed_on"),
            review_method=_string(raw_truth, "review_method"),
            source_hashes=tuple(
                item.locator.source_sha256 for item in qrel_models
            ),
            data=_string(raw_case, "truth_sha256"),
        )
        abstention_required = bool(raw_truth.get("abstention_expected"))
        return EvaluationCaseTruth(
            case_id=case_id,
            split=EvaluationSplit.development,
            archetype=_string(raw_case, "category"),
            difficulty=(
                "multi-source" if len({item.locator.source_id for item in qrel_models}) > 1 else "single-source"
            ),
            evidence_condition="reviewed-exact-content",
            query=EvaluationQuery(
                query_id=question_id,
                text=_string(raw_case, "question"),
                provenance=case_provenance,
            ),
            qrels=qrel_models,
            claims=claim_models,
            conflict=ConflictExpectation(
                conflict_expected=False,
                rationale=(
                    "Conflict and limitation expectations are retained as typed claim-evidence relations; this case declares no pair of mutually exclusive truth claims."
                ),
            ),
            abstention_expectation=(
                AbstentionExpectation.required
                if abstention_required
                else AbstentionExpectation.prohibited
            ),
            provenance=case_provenance,
        )

    @staticmethod
    def _qrel(
        raw: Mapping[str, object],
        *,
        question_id: str,
        rationale: str,
        relevance_grade: int,
        source_uris: Mapping[str, str],
    ) -> QrelJudgment:
        source_id = _string(raw, "source_id")
        source_uri = source_uris.get(source_id)
        if source_uri is None or not source_uri.strip():
            raise ResearchTruthAdaptationError(
                f"reviewed qrel source URI is missing: {source_id}"
            )
        chunk = _mapping(raw, "chunk")
        exact_text = _string(chunk, "normalized_text")
        qrel_id = _string(raw, "qrel_id")
        provenance = _provenance(
            reviewer_id=_string(raw, "adjudicator_id"),
            reviewed_on=_string(raw, "reviewed_on"),
            review_method=_string(raw, "review_method"),
            source_hashes=(_string(raw, "source_sha256"),),
            data=_string(raw, "qrel_identity_sha256"),
        )
        return QrelJudgment(
            qrel_id=qrel_id,
            query_id=question_id,
            relevance_grade=relevance_grade,
            locator=ExactEvidenceLocator(
                locator_id=qrel_id,
                source_id=source_id,
                source_uri=source_uri,
                source_sha256=_string(raw, "source_sha256"),
                chunk_id=_string(chunk, "chunk_id"),
                character_start=0,
                character_end=len(exact_text),
                exact_text=exact_text,
                exact_text_sha256=_string(chunk, "normalized_text_sha256"),
            ),
            rationale=rationale,
            provenance=provenance,
        )

    @staticmethod
    def _claim(
        raw: Mapping[str, object],
        *,
        index: int,
        case_id: str,
        question_id: str,
        qrels_by_id: Mapping[str, Mapping[str, object]],
        raw_claims: Mapping[str, object],
    ) -> AtomicClaimTruth:
        role = _string(raw, "claim_role")
        if role not in {"expected-answer", "abstention-reason"}:
            raise ResearchTruthAdaptationError(f"unknown question claim role: {role}")
        citations = tuple(
            CitationTruthLabel(
                citation_label_id=f"{case_id}::point::{index:02d}::citation::{ordinal:02d}",
                qrel_id=_string(item, "qrel_id"),
                relation=CitationTruthRelation(_string(item, "relation")),
                rationale=(
                    "Source-first review binds this exact qrel relation to the frozen answer point."
                ),
                provenance=_provenance(
                    reviewer_id=_string(raw_claims, "reviewer_id"),
                    reviewed_on=_string(raw_claims, "reviewed_on"),
                    review_method=_string(raw_claims, "review_method"),
                    source_hashes=(
                        _string(qrels_by_id[_string(item, "qrel_id")], "source_sha256"),
                    ),
                    data=content_artifact_id(dict(raw)).removeprefix("sha256:"),
                ),
            )
            for ordinal, item in enumerate(_mapping_sequence(raw, "citations"))
        )
        expected = role == "expected-answer"
        return AtomicClaimTruth(
            claim_truth_id=f"{case_id}::point::{index:02d}",
            query_id=question_id,
            statement=_string(raw, "statement"),
            claim_class=(ClaimTruthClass.expected if expected else ClaimTruthClass.forbidden),
            expected_in_answer=expected,
            abstention_expectation=(
                AbstentionExpectation.prohibited
                if expected
                else AbstentionExpectation.required
            ),
            citations=citations,
            rationale=(
                "This independently reviewed point is required in a grounded answer."
                if expected
                else "This independently reviewed point defines the grounded abstention rationale, not an asserted answer."
            ),
            provenance=_provenance(
                reviewer_id=_string(raw_claims, "reviewer_id"),
                reviewed_on=_string(raw_claims, "reviewed_on"),
                review_method=_string(raw_claims, "review_method"),
                source_hashes=tuple(
                    _string(qrels_by_id[_string(item, "qrel_id")], "source_sha256")
                    for item in _mapping_sequence(raw, "citations")
                ),
                data=content_artifact_id(dict(raw)).removeprefix("sha256:"),
            ),
        )


def _provenance(
    *,
    reviewer_id: str,
    reviewed_on: str,
    review_method: str,
    source_hashes: tuple[str, ...],
    data: str,
) -> TruthProvenance:
    return TruthProvenance(
        reviewer_ids=(reviewer_id,),
        reviewed_on=date.fromisoformat(reviewed_on),
        review_method=review_method,
        source_identity_sha256=hashlib.sha256(
            "\n".join(sorted(set(source_hashes))).encode("utf-8")
        ).hexdigest(),
        data_identity_sha256=data,
    )


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ResearchTruthAdaptationError(f"research truth field is not an object: {key}")
    return item


def _mapping_sequence(
    value: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    item = value.get(key)
    if not isinstance(item, list) or not all(
        isinstance(element, Mapping) for element in item
    ):
        raise ResearchTruthAdaptationError(f"research truth field is not a list: {key}")
    return tuple(element for element in item if isinstance(element, Mapping))


def _values(value: Mapping[str, object], key: str) -> tuple[object, ...]:
    item = value.get(key)
    if not isinstance(item, list):
        raise ResearchTruthAdaptationError(f"research truth field is not a list: {key}")
    return tuple(item)


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ResearchTruthAdaptationError(f"research truth field is not text: {key}")
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ResearchTruthAdaptationError(f"research truth field is not an integer: {key}")
    return item


__all__ = ["ResearchQuestionTruthAdapter", "ResearchTruthAdaptationError"]
