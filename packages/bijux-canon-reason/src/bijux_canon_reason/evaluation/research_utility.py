# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Paired one-pass RAG and bounded-research utility evaluation."""

from __future__ import annotations

import hashlib
from typing import Annotated, Self

from pydantic import Field, StringConstraints, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.claim_faithfulness import ClaimFaithfulnessReport
from bijux_canon_reason.evaluation.product_metrics import (
    ProductAnswerDisposition,
    ProductEvaluationCase,
    ProductExecutionStatus,
    ProductMetricMeasurement,
    ProductMetricReport,
    UnconditionalProductMetricEvaluator,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research import (
    AnswerVerificationStatus,
    ConvergenceReason,
    ResearchConvergenceEvidence,
)

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
_COUNTEREVIDENCE_RECALL_MINIMUM = 0.90
_EXPECTED_CLAIM_GAIN_MINIMUM = 0.05
_UNSUPPORTED_RATE_DELTA_MAXIMUM = 0.0
_REQUIREMENT_COVERAGE_MINIMUM = 1.0
_CLASSIFICATION_COMPLETENESS_MINIMUM = 1.0
_COMPLETED_MATERIAL_CLOSURE_MINIMUM = 1.0


class PairedResearchBinding(StableModel):
    """Exact question, corpus, and base retrieval shared by RAG and RAR."""

    question_sha256: Sha256
    corpus_artifact_id: str
    base_retrieval_artifact_id: str
    retrieval_config_sha256: Sha256

    @field_validator("corpus_artifact_id", "base_retrieval_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)


class PairedResearchCase(StableModel):
    """Identical-input RAG/RAR outputs plus bounded execution observations."""

    case_id: str
    rag_binding: PairedResearchBinding
    rar_binding: PairedResearchBinding
    source_identity_sha256: Sha256
    model_identity_sha256: Sha256
    config_identity_sha256: Sha256
    rag_faithfulness: ClaimFaithfulnessReport
    rar_faithfulness: ClaimFaithfulnessReport
    expected_counterevidence_qrel_ids: tuple[str, ...]
    rar_counterevidence_qrel_ids: tuple[str, ...]
    rar_convergence_evidence: ResearchConvergenceEvidence
    rar_convergence_reasons: tuple[ConvergenceReason, ...]
    rar_answer_changed: bool
    rag_cost_usd: float = Field(ge=0.0)
    rar_cost_usd: float = Field(ge=0.0)
    rag_latency_ms: int = Field(ge=0)
    rar_latency_ms: int = Field(ge=0)
    rar_iterations: int = Field(gt=0)
    rag_tool_calls: int = Field(ge=0)
    rar_tool_calls: int = Field(ge=0)
    rag_execution_status: ProductExecutionStatus = ProductExecutionStatus.completed
    rar_execution_status: ProductExecutionStatus = ProductExecutionStatus.completed
    rag_failure_code: str | None = None
    rar_failure_code: str | None = None
    rar_answer_disposition: ProductAnswerDisposition = ProductAnswerDisposition.answered
    label_completeness: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_pair(self) -> Self:
        reports = (self.rag_faithfulness, self.rar_faithfulness)
        if any(report.case_id != self.case_id for report in reports):
            raise ValueError("paired faithfulness reports belong to another case")
        if reports[0].system_output_id == reports[1].system_output_id:
            raise ValueError("paired RAG and RAR outputs must be distinct")
        if self.rag_binding != self.rar_binding:
            raise ValueError(
                "paired RAG and RAR must share question, corpus, retrieval, and config"
            )
        if len(set(self.expected_counterevidence_qrel_ids)) != len(
            self.expected_counterevidence_qrel_ids
        ):
            raise ValueError("expected counterevidence qrel IDs must be unique")
        if len(set(self.rar_counterevidence_qrel_ids)) != len(
            self.rar_counterevidence_qrel_ids
        ):
            raise ValueError("retrieved counterevidence qrel IDs must be unique")
        if (
            not self.rar_convergence_reasons
            or tuple(sorted(set(self.rar_convergence_reasons)))
            != self.rar_convergence_reasons
        ):
            raise ValueError(
                "RAR convergence reasons must be nonempty, unique, and sorted"
            )
        if (
            self.rar_answer_changed
            and self.rar_convergence_evidence.answer_revision_artifact_id is None
        ):
            raise ValueError("a changed RAR answer requires a revision identity")
        for owner, status, failure_code in (
            ("RAG", self.rag_execution_status, self.rag_failure_code),
            ("RAR", self.rar_execution_status, self.rar_failure_code),
        ):
            incomplete = status is not ProductExecutionStatus.completed
            if incomplete != (failure_code is not None):
                raise ValueError(
                    f"{owner} non-completion requires exactly one typed failure code"
                )
        if (self.rar_execution_status is ProductExecutionStatus.completed) != (
            self.rar_answer_disposition is not ProductAnswerDisposition.not_produced
        ):
            raise ValueError("RAR answer disposition conflicts with execution status")
        return self


class ResearchUtilityCaseOutcome(StableModel):
    """Per-case paired quality, cost, latency, and convergence values."""

    case_id: str
    counterevidence_found: int
    counterevidence_expected: int
    requirement_satisfied: int
    requirement_expected: int
    classified_candidates: int
    material_candidates: int
    unresolved_classification_count: int
    blocking_gap_count: int
    unsearched_material_count: int
    material_conflict_count: int
    answer_verification_status: AnswerVerificationStatus
    revision_artifact_id: str | None
    answer_changed: bool
    rag_expected_claim_recall: float
    rar_expected_claim_recall: float
    rag_unsupported_claim_rate: float
    rar_unsupported_claim_rate: float
    rag_cost_usd: float
    rar_cost_usd: float
    rag_latency_ms: int
    rar_latency_ms: int
    rar_iterations: int
    rag_tool_calls: int
    rar_tool_calls: int
    rar_convergence_reasons: tuple[ConvergenceReason, ...]
    rag_execution_status: ProductExecutionStatus
    rar_execution_status: ProductExecutionStatus
    rar_failure_code: str | None


class ResearchUtilityMetric(StableModel):
    """One exact paired research-utility threshold."""

    metric_id: str
    value: float
    threshold: float
    lower_is_better: bool
    formula: str
    passed: bool

    @model_validator(mode="after")
    def _validate_threshold(self) -> Self:
        expected = (
            self.value <= self.threshold
            if self.lower_is_better
            else self.value >= self.threshold
        )
        if self.passed != expected:
            raise ValueError("research utility threshold status is inconsistent")
        return self


class ResearchUtilityReport(StableModel):
    """Content-addressed paired utility result for the frozen research subset."""

    schema_version: str = "bijux.canon.evaluation.research-utility.v3"
    artifact_id: str
    input_identity_sha256: str
    outcomes: tuple[ResearchUtilityCaseOutcome, ...]
    counterevidence_recall: ResearchUtilityMetric
    expected_claim_recall_gain: ResearchUtilityMetric
    unsupported_claim_rate_delta: ResearchUtilityMetric
    requirement_coverage: ResearchUtilityMetric
    classification_completeness: ResearchUtilityMetric
    completed_material_closure: ResearchUtilityMetric
    rag_total_cost_usd: float
    rar_total_cost_usd: float
    rag_total_latency_ms: int
    rar_total_latency_ms: int
    rar_total_iterations: int
    rag_total_tool_calls: int
    rar_total_tool_calls: int
    unconditional_metrics: ProductMetricReport
    passed: bool

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if not self.outcomes or len({item.case_id for item in self.outcomes}) != len(
            self.outcomes
        ):
            raise ValueError("research utility outcomes must be nonempty and unique")
        metrics = (
            self.counterevidence_recall,
            self.expected_claim_recall_gain,
            self.unsupported_claim_rate_delta,
            self.requirement_coverage,
            self.classification_completeness,
            self.completed_material_closure,
        )
        if tuple(item.metric_id for item in metrics) != (
            "rar-counterevidence-recall",
            "rar-expected-claim-gain",
            "rar-unsupported-rate-delta",
            "rar-requirement-coverage",
            "rar-classification-completeness",
            "rar-completed-material-closure",
        ):
            raise ValueError("research utility dimensions are incomplete")
        if self.passed != (
            all(metric.passed for metric in metrics)
            and self.unconditional_metrics.passed
        ):
            raise ValueError("research utility report status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("research utility report identity does not match")
        return self


class ResearchUtilityEvaluationError(ValueError):
    """Paired research cases are empty or duplicate a case identity."""


class ResearchUtilityEvaluator:
    """Compare bounded research with one-pass RAG on identical cases."""

    def evaluate(self, cases: tuple[PairedResearchCase, ...]) -> ResearchUtilityReport:
        """Compute paired gains while retaining every case and resource observation."""
        if not cases:
            raise ResearchUtilityEvaluationError("research utility requires cases")
        if len({item.case_id for item in cases}) != len(cases):
            raise ResearchUtilityEvaluationError(
                "research utility case IDs must be unique"
            )
        outcomes = tuple(_outcome(item) for item in cases)
        found = sum(item.counterevidence_found for item in outcomes)
        expected = sum(item.counterevidence_expected for item in outcomes)
        counter_recall = 1.0 if expected == 0 else found / expected
        rag_expected = _expected_recall(cases, rar=False)
        rar_expected = _expected_recall(cases, rar=True)
        expected_gain = rar_expected - rag_expected
        rag_unsupported = _unsupported_rate(cases, rar=False)
        rar_unsupported = _unsupported_rate(cases, rar=True)
        unsupported_delta = rar_unsupported - rag_unsupported
        metrics = (
            _metric(
                "rar-counterevidence-recall",
                counter_recall,
                _COUNTEREVIDENCE_RECALL_MINIMUM,
                False,
                "distinct reviewed counterevidence qrels found by RAR / all reviewed counterevidence qrels",
            ),
            _metric(
                "rar-expected-claim-gain",
                expected_gain,
                _EXPECTED_CLAIM_GAIN_MINIMUM,
                False,
                "RAR expected-claim recall minus paired RAG expected-claim recall",
            ),
            _metric(
                "rar-unsupported-rate-delta",
                unsupported_delta,
                _UNSUPPORTED_RATE_DELTA_MAXIMUM,
                True,
                "RAR unsupported-claim rate minus paired RAG unsupported-claim rate",
            ),
            _metric(
                "rar-requirement-coverage",
                _ratio(
                    sum(item.requirement_satisfied for item in outcomes),
                    sum(item.requirement_expected for item in outcomes),
                ),
                _REQUIREMENT_COVERAGE_MINIMUM,
                False,
                "satisfied material answer requirements / all material answer requirements",
            ),
            _metric(
                "rar-classification-completeness",
                _ratio(
                    sum(item.classified_candidates for item in outcomes),
                    sum(item.material_candidates for item in outcomes),
                ),
                _CLASSIFICATION_COMPLETENESS_MINIMUM,
                False,
                "classified material candidates / all material candidates",
            ),
            _metric(
                "rar-completed-material-closure",
                _completed_material_closure(outcomes),
                _COMPLETED_MATERIAL_CLOSURE_MINIMUM,
                False,
                "completed cases with no remaining material requirement, classification, or search work / completed cases",
            ),
        )
        input_identity = hashlib.sha256(
            "\n".join(
                f"{item.case_id}:{content_artifact_id(item.rag_binding.model_dump(mode='json'))}"
                for item in sorted(cases, key=lambda candidate: candidate.case_id)
            ).encode("utf-8")
        ).hexdigest()
        rag_total_cost = sum(item.rag_cost_usd for item in cases)
        rar_total_cost = sum(item.rar_cost_usd for item in cases)
        rag_total_latency = sum(item.rag_latency_ms for item in cases)
        rar_total_latency = sum(item.rar_latency_ms for item in cases)
        rar_total_iterations = sum(item.rar_iterations for item in cases)
        rag_total_tool_calls = sum(item.rag_tool_calls for item in cases)
        rar_total_tool_calls = sum(item.rar_tool_calls for item in cases)
        unconditional = _unconditional_report(cases, outcomes, input_identity)
        passed = all(metric.passed for metric in metrics) and unconditional.passed
        payload = {
            "schema_version": "bijux.canon.evaluation.research-utility.v3",
            "input_identity_sha256": input_identity,
            "outcomes": tuple(item.model_dump(mode="json") for item in outcomes),
            "counterevidence_recall": metrics[0].model_dump(mode="json"),
            "expected_claim_recall_gain": metrics[1].model_dump(mode="json"),
            "unsupported_claim_rate_delta": metrics[2].model_dump(mode="json"),
            "requirement_coverage": metrics[3].model_dump(mode="json"),
            "classification_completeness": metrics[4].model_dump(mode="json"),
            "completed_material_closure": metrics[5].model_dump(mode="json"),
            "rag_total_cost_usd": rag_total_cost,
            "rar_total_cost_usd": rar_total_cost,
            "rag_total_latency_ms": rag_total_latency,
            "rar_total_latency_ms": rar_total_latency,
            "rar_total_iterations": rar_total_iterations,
            "rag_total_tool_calls": rag_total_tool_calls,
            "rar_total_tool_calls": rar_total_tool_calls,
            "unconditional_metrics": unconditional.model_dump(mode="json"),
            "passed": passed,
        }
        return ResearchUtilityReport(
            artifact_id=content_artifact_id(payload),
            input_identity_sha256=input_identity,
            outcomes=outcomes,
            counterevidence_recall=metrics[0],
            expected_claim_recall_gain=metrics[1],
            unsupported_claim_rate_delta=metrics[2],
            requirement_coverage=metrics[3],
            classification_completeness=metrics[4],
            completed_material_closure=metrics[5],
            rag_total_cost_usd=rag_total_cost,
            rar_total_cost_usd=rar_total_cost,
            rag_total_latency_ms=rag_total_latency,
            rar_total_latency_ms=rar_total_latency,
            rar_total_iterations=rar_total_iterations,
            rag_total_tool_calls=rag_total_tool_calls,
            rar_total_tool_calls=rar_total_tool_calls,
            unconditional_metrics=unconditional,
            passed=passed,
        )


def _outcome(item: PairedResearchCase) -> ResearchUtilityCaseOutcome:
    expected = set(item.expected_counterevidence_qrel_ids)
    evidence = item.rar_convergence_evidence
    completed = item.rar_execution_status is ProductExecutionStatus.completed
    rag_completed = item.rag_execution_status is ProductExecutionStatus.completed
    found = (
        expected.intersection(item.rar_counterevidence_qrel_ids) if completed else set()
    )
    return ResearchUtilityCaseOutcome(
        case_id=item.case_id,
        counterevidence_found=len(found),
        counterevidence_expected=len(expected),
        requirement_satisfied=len(evidence.satisfied_requirement_artifact_ids),
        requirement_expected=evidence.material_requirement_count,
        classified_candidates=evidence.classified_candidate_count,
        material_candidates=evidence.material_candidate_count,
        unresolved_classification_count=len(
            evidence.unresolved_classification_artifact_ids
        ),
        blocking_gap_count=len(evidence.blocking_gap_artifact_ids),
        unsearched_material_count=len(evidence.unsearched_important_claim_artifact_ids),
        material_conflict_count=evidence.material_conflict_count,
        answer_verification_status=evidence.answer_verification_status,
        revision_artifact_id=evidence.answer_revision_artifact_id,
        answer_changed=item.rar_answer_changed,
        rag_expected_claim_recall=(
            item.rag_faithfulness.expected_claim_recall.value if rag_completed else 0.0
        ),
        rar_expected_claim_recall=(
            item.rar_faithfulness.expected_claim_recall.value if completed else 0.0
        ),
        rag_unsupported_claim_rate=(
            1.0 - item.rag_faithfulness.supported_claim_coverage.value
            if rag_completed
            else 1.0
        ),
        rar_unsupported_claim_rate=(
            1.0 - item.rar_faithfulness.supported_claim_coverage.value
            if completed
            else 1.0
        ),
        rag_cost_usd=item.rag_cost_usd,
        rar_cost_usd=item.rar_cost_usd,
        rag_latency_ms=item.rag_latency_ms,
        rar_latency_ms=item.rar_latency_ms,
        rar_iterations=item.rar_iterations,
        rag_tool_calls=item.rag_tool_calls,
        rar_tool_calls=item.rar_tool_calls,
        rar_convergence_reasons=item.rar_convergence_reasons,
        rag_execution_status=item.rag_execution_status,
        rar_execution_status=item.rar_execution_status,
        rar_failure_code=item.rar_failure_code,
    )


def _expected_recall(cases: tuple[PairedResearchCase, ...], *, rar: bool) -> float:
    reports = tuple(
        item.rar_faithfulness if rar else item.rag_faithfulness for item in cases
    )
    numerator = sum(
        0 if not _completed(case, rar=rar) else report.expected_claim_recall.numerator
        for case, report in zip(cases, reports, strict=True)
    )
    denominator = sum(item.expected_claim_recall.denominator for item in reports)
    return 1.0 if denominator == 0 else numerator / denominator


def _unsupported_rate(cases: tuple[PairedResearchCase, ...], *, rar: bool) -> float:
    reports = tuple(
        item.rar_faithfulness if rar else item.rag_faithfulness for item in cases
    )
    supported = sum(
        0
        if not _completed(case, rar=rar)
        else report.supported_claim_coverage.numerator
        for case, report in zip(cases, reports, strict=True)
    )
    claims = sum(
        (
            max(
                report.supported_claim_coverage.denominator,
                report.expected_claim_recall.denominator,
                1,
            )
            if not _completed(case, rar=rar)
            else report.supported_claim_coverage.denominator
        )
        for case, report in zip(cases, reports, strict=True)
    )
    return 0.0 if claims == 0 else (claims - supported) / claims


def _unconditional_report(
    cases: tuple[PairedResearchCase, ...],
    outcomes: tuple[ResearchUtilityCaseOutcome, ...],
    input_identity: str,
) -> ProductMetricReport:
    product_cases = tuple(
        ProductEvaluationCase(
            case_id=item.case_id,
            execution_status=item.rar_execution_status,
            answer_disposition=(
                item.rar_answer_disposition
                if item.rar_execution_status is ProductExecutionStatus.completed
                else ProductAnswerDisposition.not_produced
            ),
            failure_code=item.rar_failure_code,
            label_completeness=item.label_completeness,
        )
        for item in cases
    )
    measurements: list[ProductMetricMeasurement] = []
    for case, outcome in zip(cases, outcomes, strict=True):
        supported = case.rar_faithfulness.supported_claim_coverage
        unsupported_denominator = max(
            supported.denominator,
            case.rar_faithfulness.expected_claim_recall.denominator,
            int(case.rar_execution_status is not ProductExecutionStatus.completed),
        )
        unsupported_numerator = (
            unsupported_denominator
            if case.rar_execution_status is not ProductExecutionStatus.completed
            else supported.denominator - supported.numerator
        )
        values = (
            (
                "counterevidence.recall",
                float(outcome.counterevidence_found),
                float(outcome.counterevidence_expected),
            ),
            (
                "revision.expected-claim-recall-gain",
                outcome.rar_expected_claim_recall - outcome.rag_expected_claim_recall,
                1.0,
            ),
            (
                "unsupported-claim.rate",
                float(unsupported_numerator),
                float(unsupported_denominator),
            ),
            (
                "latency.warm-hybrid-operator-p95-ms",
                float(outcome.rar_latency_ms),
                1.0,
            ),
        )
        measurements.extend(
            ProductMetricMeasurement(
                metric_id=metric_id,
                case_id=case.case_id,
                numerator=numerator,
                denominator=denominator,
            )
            for metric_id, numerator, denominator in values
        )
    return UnconditionalProductMetricEvaluator().evaluate(
        cases=product_cases,
        measurements=tuple(measurements),
        source_identity_sha256=_population_identity(cases, "source_identity_sha256"),
        data_identity_sha256=input_identity,
        model_identity_sha256=_population_identity(cases, "model_identity_sha256"),
        config_identity_sha256=_population_identity(cases, "config_identity_sha256"),
        metric_ids=(
            "counterevidence.recall",
            "revision.expected-claim-recall-gain",
            "unsupported-claim.rate",
            "latency.warm-hybrid-operator-p95-ms",
        ),
    )


def _completed(case: PairedResearchCase, *, rar: bool) -> bool:
    status = case.rar_execution_status if rar else case.rag_execution_status
    return status is ProductExecutionStatus.completed


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def _completed_material_closure(
    outcomes: tuple[ResearchUtilityCaseOutcome, ...],
) -> float:
    completed = tuple(
        item
        for item in outcomes
        if item.rar_execution_status is ProductExecutionStatus.completed
    )
    closed = sum(
        item.requirement_satisfied == item.requirement_expected
        and item.classified_candidates == item.material_candidates
        and item.unresolved_classification_count == 0
        and item.blocking_gap_count == 0
        and item.unsearched_material_count == 0
        for item in completed
    )
    return _ratio(closed, len(completed))


def _population_identity(
    cases: tuple[PairedResearchCase, ...],
    field: str,
) -> str:
    return hashlib.sha256(
        "\n".join(
            f"{item.case_id}:{getattr(item, field)}"
            for item in sorted(cases, key=lambda candidate: candidate.case_id)
        ).encode()
    ).hexdigest()


def _metric(
    metric_id: str,
    value: float,
    threshold: float,
    lower_is_better: bool,
    formula: str,
) -> ResearchUtilityMetric:
    passed = value <= threshold if lower_is_better else value >= threshold
    return ResearchUtilityMetric(
        metric_id=metric_id,
        value=value,
        threshold=threshold,
        lower_is_better=lower_is_better,
        formula=formula,
        passed=passed,
    )


__all__ = [
    "PairedResearchBinding",
    "PairedResearchCase",
    "ResearchUtilityCaseOutcome",
    "ResearchUtilityEvaluationError",
    "ResearchUtilityEvaluator",
    "ResearchUtilityMetric",
    "ResearchUtilityReport",
]
