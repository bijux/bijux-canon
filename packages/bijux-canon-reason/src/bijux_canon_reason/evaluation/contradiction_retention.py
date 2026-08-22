# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Conflict and qualification retention across graph synthesis and final answers."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.outcomes import SystemOutput
from bijux_canon_reason.evaluation.truth import (
    Identifier,
    NonEmptyText,
    TruthProvenance,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.graph_synthesis import VerifiedGraphSynthesis


class RetentionKind(StrEnum):
    """Reviewed information that must survive graph-to-answer synthesis."""

    conflict = "conflict"
    study_limit = "study-limit"
    population_scope = "population-scope"
    assumption = "assumption"
    unresolved_gap = "unresolved-gap"


class RetentionTruthItem(StableModel):
    """One independently reviewed exact statement and required graph location."""

    retention_id: Identifier
    kind: RetentionKind
    statement: NonEmptyText


class ContradictionRetentionTruth(StableModel):
    """Source-first expectations for one seeded-conflict evaluation case."""

    schema_version: str = "bijux.canon.evaluation.contradiction-truth.v1"
    artifact_id: str
    case_id: Identifier
    items: tuple[RetentionTruthItem, ...] = Field(min_length=1)
    provenance: TruthProvenance

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_truth(self) -> Self:
        if len({item.retention_id for item in self.items}) != len(self.items):
            raise ValueError("retention truth IDs must be unique")
        if len({(item.kind, item.statement) for item in self.items}) != len(self.items):
            raise ValueError("retention truth statements must be unique per kind")
        if RetentionKind.conflict not in {item.kind for item in self.items}:
            raise ValueError("contradiction truth requires a seeded conflict")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("contradiction truth identity does not match")
        return self


class RetentionOutcome(StableModel):
    """Graph and final-answer retention for one reviewed statement."""

    retention_id: str
    kind: RetentionKind
    graph_retained: bool
    answer_retained: bool
    false_consensus: bool
    passed: bool

    @model_validator(mode="after")
    def _validate_outcome(self) -> Self:
        if self.false_consensus and self.kind is not RetentionKind.conflict:
            raise ValueError("false consensus applies only to conflict truth")
        expected = (
            self.graph_retained and self.answer_retained and not self.false_consensus
        )
        if self.passed != expected:
            raise ValueError("retention outcome status is inconsistent")
        return self


class ContradictionRetentionMetric(StableModel):
    """Exact preservation or false-consensus arithmetic."""

    metric_id: str
    numerator: int
    denominator: int
    value: float
    threshold: float
    lower_is_better: bool
    formula: str
    passed: bool

    @model_validator(mode="after")
    def _validate_metric(self) -> Self:
        if self.denominator <= 0 or not 0 <= self.numerator <= self.denominator:
            raise ValueError("contradiction metric counts are invalid")
        if self.value != self.numerator / self.denominator:
            raise ValueError("contradiction metric value does not match arithmetic")
        expected = (
            self.value <= self.threshold
            if self.lower_is_better
            else self.value >= self.threshold
        )
        if self.passed != expected:
            raise ValueError("contradiction metric threshold status is inconsistent")
        return self


class ContradictionRetentionReport(StableModel):
    """Content-addressed conflict and qualification retention result."""

    schema_version: str = "bijux.canon.evaluation.contradiction-retention.v1"
    artifact_id: str
    truth_artifact_id: str
    graph_synthesis_artifact_id: str
    system_output_id: str
    outcomes: tuple[RetentionOutcome, ...]
    retention: ContradictionRetentionMetric
    false_consensus: ContradictionRetentionMetric
    passed: bool

    @field_validator("artifact_id", "truth_artifact_id", "graph_synthesis_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if len({item.retention_id for item in self.outcomes}) != len(self.outcomes):
            raise ValueError("retention outcomes must be unique")
        if self.retention.metric_id != "contradiction-retention":
            raise ValueError("contradiction retention metric is missing")
        if self.false_consensus.metric_id != "false-consensus":
            raise ValueError("false consensus metric is missing")
        if self.passed != (self.retention.passed and self.false_consensus.passed):
            raise ValueError("contradiction report status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("contradiction report identity does not match")
        return self


class ContradictionRetentionEvaluationError(ValueError):
    """Graph, output, and reviewed contradiction truth do not share identity."""


class ContradictionRetentionEvaluator:
    """Require seeded conflicts and qualifications in graph and final answer."""

    def evaluate(
        self,
        *,
        truth: ContradictionRetentionTruth,
        synthesis: VerifiedGraphSynthesis,
        output: SystemOutput,
    ) -> ContradictionRetentionReport:
        """Measure exact retention and reject conflict claims presented as consensus."""
        if output.case_id != truth.case_id:
            raise ContradictionRetentionEvaluationError(
                "system output belongs to another contradiction case"
            )
        if output.answer != synthesis.answer:
            raise ContradictionRetentionEvaluationError(
                "system output is not the evaluated graph synthesis answer"
            )
        consensus = {item.statement for item in synthesis.consensus}
        graph_statements = {
            RetentionKind.conflict: {
                item.statement for item in synthesis.conflicted_claims
            }
            | {item.statement for item in synthesis.conflicts},
            RetentionKind.study_limit: {
                item.statement for item in synthesis.limitations
            },
            RetentionKind.population_scope: {
                item.statement for item in synthesis.limitations
            }
            | {item.statement for item in synthesis.conflicts},
            RetentionKind.assumption: {
                item.statement for item in synthesis.assumptions
            },
            RetentionKind.unresolved_gap: {
                item.description for item in synthesis.remaining_gaps
            },
        }
        outcomes = tuple(
            RetentionOutcome(
                retention_id=item.retention_id,
                kind=item.kind,
                graph_retained=item.statement in graph_statements[item.kind],
                answer_retained=item.statement in output.answer,
                false_consensus=(
                    item.kind is RetentionKind.conflict and item.statement in consensus
                ),
                passed=(
                    item.statement in graph_statements[item.kind]
                    and item.statement in output.answer
                    and not (
                        item.kind is RetentionKind.conflict
                        and item.statement in consensus
                    )
                ),
            )
            for item in truth.items
        )
        retained = sum(
            item.graph_retained and item.answer_retained for item in outcomes
        )
        conflicts = tuple(
            item for item in outcomes if item.kind is RetentionKind.conflict
        )
        false_consensus_count = sum(item.false_consensus for item in conflicts)
        retention = ContradictionRetentionMetric(
            metric_id="contradiction-retention",
            numerator=retained,
            denominator=len(outcomes),
            value=retained / len(outcomes),
            threshold=1.0,
            lower_is_better=False,
            formula="reviewed items retained in structured graph and final answer / all reviewed items",
            passed=retained == len(outcomes),
        )
        false_consensus = ContradictionRetentionMetric(
            metric_id="false-consensus",
            numerator=false_consensus_count,
            denominator=len(conflicts),
            value=false_consensus_count / len(conflicts),
            threshold=0.0,
            lower_is_better=True,
            formula="seeded conflict statements emitted as consensus / all seeded conflict statements",
            passed=false_consensus_count == 0,
        )
        payload = {
            "schema_version": "bijux.canon.evaluation.contradiction-retention.v1",
            "truth_artifact_id": truth.artifact_id,
            "graph_synthesis_artifact_id": synthesis.artifact_id,
            "system_output_id": output.output_id,
            "outcomes": tuple(item.model_dump(mode="json") for item in outcomes),
            "retention": retention.model_dump(mode="json"),
            "false_consensus": false_consensus.model_dump(mode="json"),
            "passed": retention.passed and false_consensus.passed,
        }
        return ContradictionRetentionReport(
            artifact_id=content_artifact_id(payload),
            truth_artifact_id=truth.artifact_id,
            graph_synthesis_artifact_id=synthesis.artifact_id,
            system_output_id=output.output_id,
            outcomes=outcomes,
            retention=retention,
            false_consensus=false_consensus,
            passed=retention.passed and false_consensus.passed,
        )


__all__ = [
    "ContradictionRetentionEvaluationError",
    "ContradictionRetentionEvaluator",
    "ContradictionRetentionMetric",
    "ContradictionRetentionReport",
    "ContradictionRetentionTruth",
    "RetentionKind",
    "RetentionOutcome",
    "RetentionTruthItem",
]
