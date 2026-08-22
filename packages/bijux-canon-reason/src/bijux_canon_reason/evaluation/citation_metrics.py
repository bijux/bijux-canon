# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Citation integrity evaluation against immutable source-first truth."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
import hashlib
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.outcomes import SystemCitation, SystemOutput
from bijux_canon_reason.evaluation.truth import (
    EvaluationCaseTruth,
    ExactEvidenceLocator,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class CitationIntegrityOwner(StrEnum):
    """Product owner responsible for one citation-integrity failure."""

    ingest = "ingest"
    reason = "reason"
    evaluation = "evaluation"


class CitationIntegrityFailureCode(StrEnum):
    """Stable failure taxonomy for exact citation reachability."""

    locator_missing = "locator_missing"
    locator_truth_conflict = "locator_truth_conflict"
    source_unavailable = "source_unavailable"
    source_hash_mismatch = "source_hash_mismatch"
    source_text_unreachable = "source_text_unreachable"
    source_binding_mismatch = "source_binding_mismatch"
    span_mismatch = "span_mismatch"
    text_hash_mismatch = "text_hash_mismatch"


class CitationIntegrityFailure(StableModel):
    """One owner-classified citation-integrity failure."""

    citation_id: str
    owner: CitationIntegrityOwner
    code: CitationIntegrityFailureCode
    detail: str


class CitationIntegrityOutcome(StableModel):
    """Integrity result for one emitted citation."""

    citation_id: str
    locator_id: str
    verified: bool
    failures: tuple[CitationIntegrityFailure, ...]

    @model_validator(mode="after")
    def _validate_status(self) -> Self:
        if self.verified == bool(self.failures):
            raise ValueError("citation integrity status does not match its failures")
        return self


class CitationIntegrityReport(StableModel):
    """Complete all-produced-citation reachability report."""

    schema_version: str = "bijux.canon.evaluation.citation-integrity.v1"
    artifact_id: str
    case_id: str
    system_output_id: str
    verified_citations: int
    total_citations: int
    integrity_ratio: float
    no_citations_produced: bool
    passed: bool
    citations: tuple[CitationIntegrityOutcome, ...]
    failures: tuple[CitationIntegrityFailure, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if self.total_citations != len(self.citations):
            raise ValueError("citation integrity denominator is incomplete")
        if self.verified_citations != sum(
            citation.verified for citation in self.citations
        ):
            raise ValueError("citation integrity numerator is incomplete")
        expected_ratio = (
            1.0
            if self.total_citations == 0
            else self.verified_citations / self.total_citations
        )
        if self.integrity_ratio != expected_ratio:
            raise ValueError("citation integrity ratio does not match its arithmetic")
        if self.no_citations_produced != (self.total_citations == 0):
            raise ValueError("citation integrity empty-output status is inconsistent")
        flattened = tuple(
            failure for citation in self.citations for failure in citation.failures
        )
        if self.failures != flattened:
            raise ValueError("citation integrity failures are not fully retained")
        if self.passed != (not self.failures):
            raise ValueError("citation integrity pass status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("citation integrity report identity does not match")
        return self


class CitationIntegrityEvaluationError(ValueError):
    """Citation integrity inputs do not identify one coherent case."""


class CitationIntegrityEvaluator:
    """Resolve every emitted citation through truth and immutable source bytes."""

    def evaluate(
        self,
        *,
        case: EvaluationCaseTruth,
        output: SystemOutput,
        source_payloads: Mapping[str, bytes],
    ) -> CitationIntegrityReport:
        """Evaluate all produced citations without awarding evidence-presence credit."""
        if output.case_id != case.case_id:
            raise CitationIntegrityEvaluationError(
                "system output belongs to another evaluation case"
            )
        locators = self._locators(case)
        outcomes = tuple(
            self._evaluate_citation(citation, locators, source_payloads)
            for citation in output.citations
        )
        failures = tuple(
            failure for outcome in outcomes for failure in outcome.failures
        )
        verified = sum(outcome.verified for outcome in outcomes)
        total = len(outcomes)
        payload = {
            "schema_version": "bijux.canon.evaluation.citation-integrity.v1",
            "case_id": case.case_id,
            "system_output_id": output.output_id,
            "verified_citations": verified,
            "total_citations": total,
            "integrity_ratio": 1.0 if total == 0 else verified / total,
            "no_citations_produced": total == 0,
            "passed": not failures,
            "citations": tuple(item.model_dump(mode="json") for item in outcomes),
            "failures": tuple(item.model_dump(mode="json") for item in failures),
        }
        return CitationIntegrityReport(
            artifact_id=content_artifact_id(payload),
            case_id=case.case_id,
            system_output_id=output.output_id,
            verified_citations=verified,
            total_citations=total,
            integrity_ratio=1.0 if total == 0 else verified / total,
            no_citations_produced=total == 0,
            passed=not failures,
            citations=outcomes,
            failures=failures,
        )

    @staticmethod
    def _locators(case: EvaluationCaseTruth) -> dict[str, ExactEvidenceLocator]:
        locators: dict[str, ExactEvidenceLocator] = {}
        for qrel in case.qrels:
            existing = locators.get(qrel.locator.locator_id)
            if existing is not None and existing != qrel.locator:
                raise CitationIntegrityEvaluationError(
                    "evaluation truth contains conflicting locator identities"
                )
            locators[qrel.locator.locator_id] = qrel.locator
        return locators

    @staticmethod
    def _evaluate_citation(
        citation: SystemCitation,
        locators: Mapping[str, ExactEvidenceLocator],
        source_payloads: Mapping[str, bytes],
    ) -> CitationIntegrityOutcome:
        locator = locators.get(citation.locator_id)
        failures: list[CitationIntegrityFailure] = []
        if locator is None:
            failures.append(
                _failure(
                    citation,
                    CitationIntegrityOwner.reason,
                    CitationIntegrityFailureCode.locator_missing,
                    "emitted locator is absent from independently reviewed truth",
                )
            )
        else:
            failures.extend(_binding_failures(citation, locator))
            source = source_payloads.get(locator.source_uri)
            if source is None:
                failures.append(
                    _failure(
                        citation,
                        CitationIntegrityOwner.ingest,
                        CitationIntegrityFailureCode.source_unavailable,
                        "immutable source payload is unavailable",
                    )
                )
            elif hashlib.sha256(source).hexdigest() != locator.source_sha256:
                failures.append(
                    _failure(
                        citation,
                        CitationIntegrityOwner.ingest,
                        CitationIntegrityFailureCode.source_hash_mismatch,
                        "immutable source payload hash differs from truth",
                    )
                )
            elif locator.exact_text.encode("utf-8") not in source:
                failures.append(
                    _failure(
                        citation,
                        CitationIntegrityOwner.ingest,
                        CitationIntegrityFailureCode.source_text_unreachable,
                        "reviewed exact text cannot be resolved in the source payload",
                    )
                )
        return CitationIntegrityOutcome(
            citation_id=citation.citation_id,
            locator_id=citation.locator_id,
            verified=not failures,
            failures=tuple(failures),
        )


def _binding_failures(
    citation: SystemCitation,
    locator: ExactEvidenceLocator,
) -> tuple[CitationIntegrityFailure, ...]:
    failures: list[CitationIntegrityFailure] = []
    if (
        citation.source_id != locator.source_id
        or citation.source_uri != locator.source_uri
        or citation.source_sha256 != locator.source_sha256
    ):
        failures.append(
            _failure(
                citation,
                CitationIntegrityOwner.reason,
                CitationIntegrityFailureCode.source_binding_mismatch,
                "citation source identity differs from reviewed truth",
            )
        )
    if (
        citation.character_start != locator.character_start
        or citation.character_end != locator.character_end
    ):
        failures.append(
            _failure(
                citation,
                CitationIntegrityOwner.reason,
                CitationIntegrityFailureCode.span_mismatch,
                "citation span differs from reviewed truth",
            )
        )
    if citation.exact_text_sha256 != locator.exact_text_sha256:
        failures.append(
            _failure(
                citation,
                CitationIntegrityOwner.reason,
                CitationIntegrityFailureCode.text_hash_mismatch,
                "citation exact-text hash differs from reviewed truth",
            )
        )
    return tuple(failures)


def _failure(
    citation: SystemCitation,
    owner: CitationIntegrityOwner,
    code: CitationIntegrityFailureCode,
    detail: str,
) -> CitationIntegrityFailure:
    return CitationIntegrityFailure(
        citation_id=citation.citation_id,
        owner=owner,
        code=code,
        detail=detail,
    )


__all__ = [
    "CitationIntegrityEvaluationError",
    "CitationIntegrityEvaluator",
    "CitationIntegrityFailure",
    "CitationIntegrityFailureCode",
    "CitationIntegrityOutcome",
    "CitationIntegrityOwner",
    "CitationIntegrityReport",
]
