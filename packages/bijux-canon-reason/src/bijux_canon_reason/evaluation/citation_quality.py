# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Citation precision and recall against reviewed claim-span relations."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.citation_metrics import CitationIntegrityReport
from bijux_canon_reason.evaluation.claim_matching import ClaimMatchReport
from bijux_canon_reason.evaluation.metrics import ConfidenceInterval
from bijux_canon_reason.evaluation.outcomes import SystemOutput
from bijux_canon_reason.evaluation.truth import EvaluationCaseTruth
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)

_PRECISION_MINIMUM = 0.95
_RECALL_MINIMUM = 0.90
_NORMAL_95 = 1.959963984540054


class CitationQualityFailureCode(StrEnum):
    """Stable per-case citation quality failure taxonomy."""

    claim_not_in_truth = "claim_not_in_truth"
    citation_not_labeled_for_claim = "citation_not_labeled_for_claim"
    citation_integrity_failed = "citation_integrity_failed"
    duplicate_reviewed_relation = "duplicate_reviewed_relation"
    expected_relation_missing = "expected_relation_missing"


class CitationQualityFailure(StableModel):
    """One emitted or expected claim-citation relation that did not match."""

    code: CitationQualityFailureCode
    system_claim_id: str | None
    system_citation_id: str | None
    truth_claim_id: str | None
    qrel_id: str | None
    detail: str


class CitationQualityMetric(StableModel):
    """Exact citation-quality arithmetic, threshold, and interval."""

    metric_id: str
    numerator: int
    denominator: int
    value: float
    threshold: float
    formula: str
    confidence_interval: ConfidenceInterval
    passed: bool

    @model_validator(mode="after")
    def _validate_arithmetic(self) -> Self:
        if self.numerator < 0 or self.denominator < 0:
            raise ValueError("citation quality counts must not be negative")
        if self.numerator > self.denominator:
            raise ValueError("citation quality numerator exceeds its denominator")
        expected = 0.0 if self.denominator == 0 else self.numerator / self.denominator
        if self.value != expected:
            raise ValueError("citation quality value does not match its arithmetic")
        if self.passed != (self.denominator > 0 and self.value >= self.threshold):
            raise ValueError("citation quality threshold status is inconsistent")
        return self


class CitationQualityReport(StableModel):
    """Precision, recall, and every failed relation for one case."""

    schema_version: str = "bijux.canon.evaluation.citation-quality.v2"
    artifact_id: str
    case_id: str
    system_output_id: str
    citation_integrity_artifact_id: str
    claim_match_artifact_id: str
    precision: CitationQualityMetric
    recall: CitationQualityMetric
    failures: tuple[CitationQualityFailure, ...]
    passed: bool

    @field_validator(
        "artifact_id", "citation_integrity_artifact_id", "claim_match_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if self.precision.metric_id != "citation-precision":
            raise ValueError("citation precision metric is missing")
        if self.recall.metric_id != "citation-recall":
            raise ValueError("citation recall metric is missing")
        if self.passed != (self.precision.passed and self.recall.passed):
            raise ValueError("citation quality pass status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("citation quality report identity does not match")
        return self


class CitationQualityEvaluationError(ValueError):
    """Citation quality inputs do not describe one coherent evaluation case."""


class CitationQualityEvaluator:
    """Score emitted links only against manually reviewed claim-span truth."""

    def evaluate(
        self,
        *,
        case: EvaluationCaseTruth,
        output: SystemOutput,
        integrity: CitationIntegrityReport,
        matching: ClaimMatchReport,
    ) -> CitationQualityReport:
        """Compute precision and recall without lexical-overlap or presence credit."""
        self._validate_inputs(case, output, integrity, matching)
        truth_claims = {claim.claim_truth_id: claim for claim in case.claims}
        matches = {item.system_claim_id: item for item in matching.outcomes}
        qrel_locators = {
            qrel.qrel_id: (qrel.locator.locator_id, qrel.locator.chunk_id)
            for qrel in case.qrels
        }
        integrity_by_citation = {
            outcome.citation_id: outcome.verified for outcome in integrity.citations
        }
        citations = {citation.citation_id: citation for citation in output.citations}
        emitted_pairs: set[tuple[str, str]] = set()
        matched_pairs: set[tuple[str, str]] = set()
        failures: list[CitationQualityFailure] = []
        for system_claim in output.claims:
            match = matches[system_claim.claim_id]
            truth_claim = (
                truth_claims.get(match.truth_claim_id)
                if match.admitted_equivalence and match.truth_claim_id is not None
                else None
            )
            allowed = (
                set()
                if truth_claim is None
                else {
                    (truth_claim.claim_truth_id, citation.qrel_id)
                    for citation in truth_claim.citations
                    if citation.qrel_id in match.reviewed_qrel_ids
                }
            )
            for citation_id in system_claim.citation_ids:
                citation = citations[citation_id]
                emitted_pairs.add((system_claim.claim_id, citation_id))
                if truth_claim is None:
                    failures.append(
                        _failure(
                            CitationQualityFailureCode.claim_not_in_truth,
                            system_claim.claim_id,
                            citation_id,
                            None,
                            None,
                            "emitted claim has no independently reviewed truth label",
                        )
                    )
                    continue
                qrel_id = next(
                    (
                        candidate_qrel_id
                        for _, candidate_qrel_id in allowed
                        if (
                            qrel_locators[candidate_qrel_id][1] == citation.chunk_id
                            if citation.schema_version.endswith(".v2")
                            else qrel_locators[candidate_qrel_id][0]
                            == citation.locator_id
                        )
                    ),
                    None,
                )
                if qrel_id is None:
                    failures.append(
                        _failure(
                            CitationQualityFailureCode.citation_not_labeled_for_claim,
                            system_claim.claim_id,
                            citation_id,
                            truth_claim.claim_truth_id,
                            None,
                            "attached citation is not a reviewed relation for the claim",
                        )
                    )
                elif not integrity_by_citation[citation_id]:
                    failures.append(
                        _failure(
                            CitationQualityFailureCode.citation_integrity_failed,
                            system_claim.claim_id,
                            citation_id,
                            truth_claim.claim_truth_id,
                            qrel_id,
                            "reviewed relation receives no credit because integrity failed",
                        )
                    )
                else:
                    truth_pair = (truth_claim.claim_truth_id, qrel_id)
                    if truth_pair in matched_pairs:
                        failures.append(
                            _failure(
                                CitationQualityFailureCode.duplicate_reviewed_relation,
                                system_claim.claim_id,
                                citation_id,
                                truth_claim.claim_truth_id,
                                qrel_id,
                                "duplicate emission receives no additional relation credit",
                            )
                        )
                    else:
                        matched_pairs.add(truth_pair)
        expected_pairs = {
            (claim.claim_truth_id, citation.qrel_id)
            for claim in case.claims
            if claim.expected_in_answer
            for citation in claim.citations
        }
        for claim_id, qrel_id in sorted(expected_pairs - matched_pairs):
            failures.append(
                _failure(
                    CitationQualityFailureCode.expected_relation_missing,
                    None,
                    None,
                    claim_id,
                    qrel_id,
                    "expected reviewed claim-span relation was not emitted",
                )
            )
        precision = _metric(
            "citation-precision",
            len(matched_pairs),
            len(emitted_pairs),
            _PRECISION_MINIMUM,
            "integrity-verified emitted claim-citation pairs matching reviewed relations / all emitted claim-citation pairs",
        )
        recall = _metric(
            "citation-recall",
            len(expected_pairs & matched_pairs),
            len(expected_pairs),
            _RECALL_MINIMUM,
            "emitted integrity-verified expected relations / all reviewed expected claim-citation relations",
        )
        payload = {
            "schema_version": "bijux.canon.evaluation.citation-quality.v2",
            "case_id": case.case_id,
            "system_output_id": output.output_id,
            "citation_integrity_artifact_id": integrity.artifact_id,
            "claim_match_artifact_id": matching.artifact_id,
            "precision": precision.model_dump(mode="json"),
            "recall": recall.model_dump(mode="json"),
            "failures": tuple(failure.model_dump(mode="json") for failure in failures),
            "passed": precision.passed and recall.passed,
        }
        return CitationQualityReport(
            artifact_id=content_artifact_id(payload),
            case_id=case.case_id,
            system_output_id=output.output_id,
            citation_integrity_artifact_id=integrity.artifact_id,
            claim_match_artifact_id=matching.artifact_id,
            precision=precision,
            recall=recall,
            failures=tuple(failures),
            passed=precision.passed and recall.passed,
        )

    @staticmethod
    def _validate_inputs(
        case: EvaluationCaseTruth,
        output: SystemOutput,
        integrity: CitationIntegrityReport,
        matching: ClaimMatchReport,
    ) -> None:
        if output.case_id != case.case_id or integrity.case_id != case.case_id:
            raise CitationQualityEvaluationError(
                "citation quality inputs belong to different cases"
            )
        if integrity.system_output_id != output.output_id:
            raise CitationQualityEvaluationError(
                "citation integrity belongs to another system output"
            )
        if (
            matching.case_id != case.case_id
            or matching.system_output_id != output.output_id
            or matching.truth_artifact_id
            != content_artifact_id(case.model_dump(mode="json"))
            or matching.system_output_artifact_id
            != content_artifact_id(output.model_dump(mode="json"))
        ):
            raise CitationQualityEvaluationError(
                "claim matching belongs to another truth or system output"
            )
        if {item.system_claim_id for item in matching.outcomes} != {
            item.claim_id for item in output.claims
        }:
            raise CitationQualityEvaluationError(
                "claim matching does not cover the exact emitted claim set"
            )
        if {item.citation_id for item in integrity.citations} != {
            item.citation_id for item in output.citations
        }:
            raise CitationQualityEvaluationError(
                "citation integrity does not cover the exact emitted citation set"
            )


def _metric(
    metric_id: str,
    numerator: int,
    denominator: int,
    threshold: float,
    formula: str,
) -> CitationQualityMetric:
    value = 0.0 if denominator == 0 else numerator / denominator
    return CitationQualityMetric(
        metric_id=metric_id,
        numerator=numerator,
        denominator=denominator,
        value=value,
        threshold=threshold,
        formula=formula,
        confidence_interval=_wilson_interval(numerator, denominator),
        passed=denominator > 0 and value >= threshold,
    )


def _wilson_interval(numerator: int, denominator: int) -> ConfidenceInterval:
    if denominator == 0:
        lower, upper = 0.0, 1.0
    else:
        proportion = numerator / denominator
        z_squared = _NORMAL_95**2
        center = (proportion + z_squared / (2 * denominator)) / (
            1 + z_squared / denominator
        )
        margin = (
            _NORMAL_95
            * math.sqrt(
                proportion * (1 - proportion) / denominator
                + z_squared / (4 * denominator**2)
            )
            / (1 + z_squared / denominator)
        )
        lower, upper = max(0.0, center - margin), min(1.0, center + margin)
    return ConfidenceInterval(
        level=0.95,
        lower=lower,
        upper=upper,
        method="Wilson score interval for a binomial proportion",
    )


def _failure(
    code: CitationQualityFailureCode,
    system_claim_id: str | None,
    system_citation_id: str | None,
    truth_claim_id: str | None,
    qrel_id: str | None,
    detail: str,
) -> CitationQualityFailure:
    return CitationQualityFailure(
        code=code,
        system_claim_id=system_claim_id,
        system_citation_id=system_citation_id,
        truth_claim_id=truth_claim_id,
        qrel_id=qrel_id,
        detail=detail,
    )


__all__ = [
    "CitationQualityEvaluationError",
    "CitationQualityEvaluator",
    "CitationQualityFailure",
    "CitationQualityFailureCode",
    "CitationQualityMetric",
    "CitationQualityReport",
]
