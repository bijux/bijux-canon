# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Atomic-claim faithfulness against reviewed truth and reachable evidence."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.citation_metrics import CitationIntegrityReport
from bijux_canon_reason.evaluation.claim_matching import (
    ClaimMatchOutcome,
    ClaimMatchRelation,
    ClaimMatchReport,
)
from bijux_canon_reason.evaluation.metrics import ConfidenceInterval, MetricDirection
from bijux_canon_reason.evaluation.outcomes import (
    SystemCitation,
    SystemClaim,
    SystemOutput,
)
from bijux_canon_reason.evaluation.truth import (
    AtomicClaimTruth,
    CitationTruthRelation,
    EvaluationCaseTruth,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)

_STATUS_COMPLETENESS_MINIMUM = 1.0
_SUPPORTED_COVERAGE_MINIMUM = 0.95
_EXPECTED_RECALL_MINIMUM = 0.90
_NONEXISTENT_EVIDENCE_MAXIMUM = 0.0
_NORMAL_95 = 1.959963984540054


class ClaimFaithfulnessStatus(StrEnum):
    """Reviewed relationship between one emitted claim and its cited evidence."""

    supported = "supported"
    opposed = "opposed"
    ambiguous = "ambiguous"
    irrelevant = "irrelevant"
    unverifiable = "unverifiable"


class ClaimFaithfulnessJudgment(StableModel):
    """Complete classification for one emitted atomic claim."""

    system_claim_id: str
    truth_claim_id: str | None
    status: ClaimFaithfulnessStatus
    reviewed_qrel_ids: tuple[str, ...]
    verified_citation_ids: tuple[str, ...]
    nonexistent_evidence: bool
    rationale: str

    @model_validator(mode="after")
    def _validate_judgment(self) -> Self:
        if not self.rationale.strip():
            raise ValueError("claim faithfulness rationale must not be empty")
        if len(set(self.reviewed_qrel_ids)) != len(self.reviewed_qrel_ids):
            raise ValueError("reviewed qrel IDs must be unique")
        if len(set(self.verified_citation_ids)) != len(self.verified_citation_ids):
            raise ValueError("verified citation IDs must be unique")
        return self


class ClaimFaithfulnessMetric(StableModel):
    """Exact arithmetic and threshold for one claim-faithfulness dimension."""

    metric_id: str
    numerator: int
    denominator: int
    value: float
    threshold: float
    direction: MetricDirection
    formula: str
    confidence_interval: ConfidenceInterval
    passed: bool

    @model_validator(mode="after")
    def _validate_arithmetic(self) -> Self:
        if self.numerator < 0 or self.denominator < 0:
            raise ValueError("claim faithfulness counts must not be negative")
        if self.numerator > self.denominator:
            raise ValueError("claim faithfulness numerator exceeds its denominator")
        expected = (
            1.0
            if self.denominator == 0
            and self.direction is MetricDirection.higher_is_better
            else 0.0
            if self.denominator == 0
            else self.numerator / self.denominator
        )
        if self.value != expected:
            raise ValueError("claim faithfulness value does not match its arithmetic")
        expected_pass = (
            self.value >= self.threshold
            if self.direction is MetricDirection.higher_is_better
            else self.value <= self.threshold
        )
        if self.passed != expected_pass:
            raise ValueError("claim faithfulness threshold status is inconsistent")
        return self


class ClaimFaithfulnessReport(StableModel):
    """Restart-safe claim judgments and exact aggregate dimensions for one case."""

    schema_version: str = "bijux.canon.evaluation.claim-faithfulness.v2"
    artifact_id: str
    case_id: str
    system_output_id: str
    citation_integrity_artifact_id: str
    claim_match_artifact_id: str
    judgments: tuple[ClaimFaithfulnessJudgment, ...]
    status_completeness: ClaimFaithfulnessMetric
    supported_claim_coverage: ClaimFaithfulnessMetric
    expected_claim_recall: ClaimFaithfulnessMetric
    nonexistent_evidence_claims: ClaimFaithfulnessMetric
    passed: bool

    @field_validator(
        "artifact_id", "citation_integrity_artifact_id", "claim_match_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        metrics = (
            self.status_completeness,
            self.supported_claim_coverage,
            self.expected_claim_recall,
            self.nonexistent_evidence_claims,
        )
        expected_ids = (
            "claim-status-completeness",
            "supported-claim-coverage",
            "expected-claim-recall",
            "nonexistent-evidence-claims",
        )
        if tuple(metric.metric_id for metric in metrics) != expected_ids:
            raise ValueError("claim faithfulness dimensions are incomplete")
        if len({item.system_claim_id for item in self.judgments}) != len(
            self.judgments
        ):
            raise ValueError("claim faithfulness judgments must be unique")
        if self.status_completeness.numerator != len(self.judgments):
            raise ValueError("claim status completeness omits judgments")
        if self.passed != all(metric.passed for metric in metrics):
            raise ValueError("claim faithfulness pass status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("claim faithfulness report identity does not match")
        return self


class ClaimFaithfulnessEvaluationError(ValueError):
    """Faithfulness inputs do not describe one coherent evaluation case."""


class ClaimFaithfulnessEvaluator:
    """Classify every emitted atomic claim without semantic proxy credit."""

    def evaluate(
        self,
        *,
        case: EvaluationCaseTruth,
        output: SystemOutput,
        integrity: CitationIntegrityReport,
        matching: ClaimMatchReport,
    ) -> ClaimFaithfulnessReport:
        """Measure exact claim status, support, recall, and evidence reachability."""
        self._validate_inputs(case, output, integrity, matching)
        truth_by_id = {claim.claim_truth_id: claim for claim in case.claims}
        matches = {item.system_claim_id: item for item in matching.outcomes}
        qrels_by_locator: dict[str, set[str]] = {}
        for qrel in case.qrels:
            qrels_by_locator.setdefault(qrel.locator.locator_id, set()).add(
                qrel.qrel_id
            )
        citations = {item.citation_id: item for item in output.citations}
        integrity_by_citation = {
            item.citation_id: item.verified for item in integrity.citations
        }
        judgments = tuple(
            self._judge(
                claim,
                matches[claim.claim_id],
                truth_by_id,
                qrels_by_locator,
                citations,
                integrity_by_citation,
            )
            for claim in output.claims
        )
        supported = sum(
            item.status is ClaimFaithfulnessStatus.supported for item in judgments
        )
        expected_ids = {
            claim.claim_truth_id for claim in case.claims if claim.expected_in_answer
        }
        recalled_ids = {
            item.truth_claim_id
            for item in judgments
            if item.status is ClaimFaithfulnessStatus.supported
            and item.truth_claim_id in expected_ids
        }
        nonexistent = sum(item.nonexistent_evidence for item in judgments)
        metrics = (
            _metric(
                "claim-status-completeness",
                len(judgments),
                len(output.claims),
                _STATUS_COMPLETENESS_MINIMUM,
                MetricDirection.higher_is_better,
                "classified emitted atomic claims / all emitted atomic claims",
            ),
            _metric(
                "supported-claim-coverage",
                supported,
                len(judgments),
                _SUPPORTED_COVERAGE_MINIMUM,
                MetricDirection.higher_is_better,
                "supported emitted atomic claims / all emitted atomic claims",
            ),
            _metric(
                "expected-claim-recall",
                len(recalled_ids),
                len(expected_ids),
                _EXPECTED_RECALL_MINIMUM,
                MetricDirection.higher_is_better,
                "distinct supported expected claims emitted / all reviewed expected claims",
            ),
            _metric(
                "nonexistent-evidence-claims",
                nonexistent,
                len(judgments),
                _NONEXISTENT_EVIDENCE_MAXIMUM,
                MetricDirection.lower_is_better,
                "claims with absent or integrity-failed evidence / all emitted atomic claims",
            ),
        )
        payload = {
            "schema_version": "bijux.canon.evaluation.claim-faithfulness.v2",
            "case_id": case.case_id,
            "system_output_id": output.output_id,
            "citation_integrity_artifact_id": integrity.artifact_id,
            "claim_match_artifact_id": matching.artifact_id,
            "judgments": tuple(item.model_dump(mode="json") for item in judgments),
            "status_completeness": metrics[0].model_dump(mode="json"),
            "supported_claim_coverage": metrics[1].model_dump(mode="json"),
            "expected_claim_recall": metrics[2].model_dump(mode="json"),
            "nonexistent_evidence_claims": metrics[3].model_dump(mode="json"),
            "passed": all(metric.passed for metric in metrics),
        }
        return ClaimFaithfulnessReport(
            artifact_id=content_artifact_id(payload),
            case_id=case.case_id,
            system_output_id=output.output_id,
            citation_integrity_artifact_id=integrity.artifact_id,
            claim_match_artifact_id=matching.artifact_id,
            judgments=judgments,
            status_completeness=metrics[0],
            supported_claim_coverage=metrics[1],
            expected_claim_recall=metrics[2],
            nonexistent_evidence_claims=metrics[3],
            passed=all(metric.passed for metric in metrics),
        )

    @staticmethod
    def _judge(
        claim: SystemClaim,
        match: ClaimMatchOutcome,
        truth_by_id: dict[str, AtomicClaimTruth],
        qrels_by_locator: dict[str, set[str]],
        citations: dict[str, SystemCitation],
        integrity_by_citation: dict[str, bool],
    ) -> ClaimFaithfulnessJudgment:
        truth = (
            None
            if match.truth_claim_id is None
            else truth_by_id[match.truth_claim_id]
        )
        typed_citations = tuple(citations[item] for item in claim.citation_ids)
        verified_ids = tuple(
            item.citation_id
            for item in typed_citations
            if integrity_by_citation[item.citation_id]
        )
        nonexistent = not claim.citation_ids or any(
            not integrity_by_citation[citation_id] for citation_id in claim.citation_ids
        )
        reviewed_qrels = {
            qrel_id
            for citation in typed_citations
            if integrity_by_citation[citation.citation_id]
            for qrel_id in qrels_by_locator.get(citation.locator_id, set())
        }
        if not match.admitted_equivalence:
            status = {
                ClaimMatchRelation.contradicts: ClaimFaithfulnessStatus.opposed,
                ClaimMatchRelation.overgeneralized: ClaimFaithfulnessStatus.ambiguous,
                ClaimMatchRelation.ambiguous: ClaimFaithfulnessStatus.ambiguous,
                ClaimMatchRelation.unrelated: ClaimFaithfulnessStatus.unverifiable,
            }.get(match.relation, ClaimFaithfulnessStatus.unverifiable)
            rationale = match.rationale
            matched_qrels: set[str] = set()
        elif not verified_ids:
            status = ClaimFaithfulnessStatus.unverifiable
            rationale = "claim has no integrity-verified cited evidence"
            matched_qrels = set()
        else:
            if truth is None:
                raise AssertionError("admitted claim match has no truth claim")
            relations = {
                label.relation
                for label in truth.citations
                if label.qrel_id in reviewed_qrels
            }
            matched_qrels = {
                label.qrel_id
                for label in truth.citations
                if label.qrel_id in reviewed_qrels
            }
            if not relations:
                status = ClaimFaithfulnessStatus.irrelevant
                rationale = "verified evidence has no reviewed relation to this claim"
            elif (
                CitationTruthRelation.supports in relations
                and CitationTruthRelation.opposes not in relations
                and not relations.intersection(
                    {CitationTruthRelation.limits, CitationTruthRelation.insufficient}
                )
            ):
                status = ClaimFaithfulnessStatus.supported
                rationale = "reviewed exact evidence supports the emitted claim"
            elif relations == {CitationTruthRelation.opposes}:
                status = ClaimFaithfulnessStatus.opposed
                rationale = "reviewed exact evidence opposes the emitted claim"
            else:
                status = ClaimFaithfulnessStatus.ambiguous
                rationale = "reviewed evidence is mixed, limiting, or insufficient"
        return ClaimFaithfulnessJudgment(
            system_claim_id=claim.claim_id,
            truth_claim_id=None if truth is None else truth.claim_truth_id,
            status=status,
            reviewed_qrel_ids=tuple(sorted(matched_qrels)),
            verified_citation_ids=verified_ids,
            nonexistent_evidence=nonexistent,
            rationale=rationale,
        )

    @staticmethod
    def _validate_inputs(
        case: EvaluationCaseTruth,
        output: SystemOutput,
        integrity: CitationIntegrityReport,
        matching: ClaimMatchReport,
    ) -> None:
        if output.case_id != case.case_id or integrity.case_id != case.case_id:
            raise ClaimFaithfulnessEvaluationError(
                "claim faithfulness inputs belong to different cases"
            )
        if integrity.system_output_id != output.output_id:
            raise ClaimFaithfulnessEvaluationError(
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
            raise ClaimFaithfulnessEvaluationError(
                "claim matching belongs to another truth or system output"
            )
        if {item.system_claim_id for item in matching.outcomes} != {
            item.claim_id for item in output.claims
        }:
            raise ClaimFaithfulnessEvaluationError(
                "claim matching does not cover the exact emitted claim set"
            )
        if {item.citation_id for item in integrity.citations} != {
            item.citation_id for item in output.citations
        }:
            raise ClaimFaithfulnessEvaluationError(
                "citation integrity does not cover the exact emitted citation set"
            )


def _metric(
    metric_id: str,
    numerator: int,
    denominator: int,
    threshold: float,
    direction: MetricDirection,
    formula: str,
) -> ClaimFaithfulnessMetric:
    value = (
        1.0
        if denominator == 0 and direction is MetricDirection.higher_is_better
        else 0.0
        if denominator == 0
        else numerator / denominator
    )
    passed = (
        value >= threshold
        if direction is MetricDirection.higher_is_better
        else value <= threshold
    )
    return ClaimFaithfulnessMetric(
        metric_id=metric_id,
        numerator=numerator,
        denominator=denominator,
        value=value,
        threshold=threshold,
        direction=direction,
        formula=formula,
        confidence_interval=_wilson_interval(numerator, denominator),
        passed=passed,
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


__all__ = [
    "ClaimFaithfulnessEvaluationError",
    "ClaimFaithfulnessEvaluator",
    "ClaimFaithfulnessJudgment",
    "ClaimFaithfulnessMetric",
    "ClaimFaithfulnessReport",
    "ClaimFaithfulnessStatus",
]
