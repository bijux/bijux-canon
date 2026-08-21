# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Admit bounded, answerable research subquestions deterministically."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import math
import re
from typing import Literal, Self
import unicodedata

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)

_SPACE = re.compile(r"\s+")
_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
_QUESTION_OPENERS = frozenset(
    {
        "are",
        "assess",
        "can",
        "compare",
        "determine",
        "did",
        "do",
        "does",
        "evaluate",
        "how",
        "identify",
        "is",
        "quantify",
        "to",
        "what",
        "when",
        "where",
        "whether",
        "which",
        "who",
        "why",
    }
)
_SIGNATURE_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "are",
        "did",
        "do",
        "does",
        "is",
        "the",
        "to",
        "what",
        "when",
        "where",
        "whether",
        "which",
        "who",
        "why",
    }
)


class ResearchQuestionIntent(StrEnum):
    """Stable intent declared by the root question contract."""

    fact = "fact"
    synthesis = "synthesis"
    comparison = "comparison"
    limitations = "limitations"
    counterevidence = "counterevidence"


class SubquestionStatus(StrEnum):
    """Initial and terminal states available to a research subquestion."""

    pending = "pending"
    active = "active"
    answered = "answered"
    insufficient = "insufficient"


class SubquestionDisposition(StrEnum):
    """Why a proposed subquestion was admitted or rejected."""

    selected = "selected"
    duplicate = "duplicate"
    overlap = "overlap"
    unanswerable = "unanswerable"
    subquestion_budget = "subquestion_budget"


class QuestionDecompositionErrorCode(StrEnum):
    """Stable failures raised before decomposition can be admitted."""

    candidate_budget_exceeded = "candidate_budget_exceeded"
    duplicate_candidate_identity = "duplicate_candidate_identity"
    root_question_too_long = "root_question_too_long"
    evidence_need_budget_exceeded = "evidence_need_budget_exceeded"


class QuestionDecompositionError(ValueError):
    """Candidate inputs violate a hard decomposition boundary."""

    def __init__(self, code: QuestionDecompositionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ResearchQuestion(StableModel):
    """A content-addressed root question from the reason v2 contract."""

    schema_version: Literal["2.0.0"]
    artifact_type: Literal["bijux.canon.reason.question"]
    artifact_id: str
    text: str
    text_sha256: str
    scope_artifact_id: str
    intent: ResearchQuestionIntent
    created_at: str

    @field_validator("artifact_id", "scope_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            raise ValueError("research question text must not be empty")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: str) -> str:
        if not value.endswith("Z"):
            raise ValueError("research question timestamp must be UTC")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if _sha256(self.text) != self.text_sha256:
            raise ValueError("research question text hash does not match")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research question identity does not match its payload")
        return self


class SubquestionCandidate(StableModel):
    """Untrusted candidate data awaiting deterministic admission."""

    schema_version: Literal["bijux.canon.reason.subquestion_candidate.v1"]
    artifact_id: str
    text: str
    text_sha256: str
    scope_artifact_id: str
    rationale: str
    evidence_needs: tuple[str, ...]
    priority: int

    @field_validator("artifact_id", "scope_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("text", "rationale")
    @classmethod
    def _validate_text_fields(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            raise ValueError("subquestion text and rationale must not be empty")
        return normalized

    @field_validator("evidence_needs")
    @classmethod
    def _validate_evidence_needs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_text(item) for item in value)
        if (
            not normalized
            or any(not item for item in normalized)
            or len(normalized) != len(set(normalized))
        ):
            raise ValueError("subquestions require unique non-empty evidence needs")
        return normalized

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("subquestion priority must be between 1 and 100")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if _sha256(self.text) != self.text_sha256:
            raise ValueError("subquestion candidate text hash does not match")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError(
                "subquestion candidate identity does not match its payload"
            )
        return self


class ResearchSubquestion(StableModel):
    """An admitted subquestion matching the reason v2 artifact contract."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    artifact_type: Literal["bijux.canon.reason.research_subquestion"] = (
        "bijux.canon.reason.research_subquestion"
    )
    artifact_id: str
    parent_question_artifact_id: str
    text: str
    text_sha256: str
    scope_artifact_id: str
    rationale: str
    evidence_needs: tuple[str, ...]
    priority: int
    status: SubquestionStatus = SubquestionStatus.pending

    @field_validator("artifact_id", "parent_question_artifact_id", "scope_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("text_sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("text", "rationale")
    @classmethod
    def _validate_text_fields(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if not normalized:
            raise ValueError("research subquestion fields must not be empty")
        return normalized

    @field_validator("evidence_needs")
    @classmethod
    def _validate_evidence_needs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalize_text(item) for item in value)
        if (
            not normalized
            or any(not item for item in normalized)
            or len(normalized) != len(set(normalized))
        ):
            raise ValueError("research subquestions require unique evidence needs")
        return normalized

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("research subquestion priority must be between 1 and 100")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if _sha256(self.text) != self.text_sha256:
            raise ValueError("research subquestion text hash does not match")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research subquestion identity does not match its payload")
        return self


class QuestionDecompositionPolicy(StableModel):
    """Hard bounds and semantic-overlap threshold for decomposition."""

    max_candidates: int = 64
    max_subquestions: int = 8
    max_question_characters: int = 2_000
    max_evidence_needs: int = 8
    min_content_tokens: int = 3
    overlap_threshold: float = 0.80

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        integers = (
            self.max_candidates,
            self.max_subquestions,
            self.max_question_characters,
            self.max_evidence_needs,
            self.min_content_tokens,
        )
        if any(value <= 0 for value in integers):
            raise ValueError("decomposition policy bounds must be positive")
        if self.max_subquestions > self.max_candidates:
            raise ValueError("subquestion budget cannot exceed candidate budget")
        if not math.isfinite(self.overlap_threshold) or not (
            0.0 < self.overlap_threshold <= 1.0
        ):
            raise ValueError("overlap threshold must be finite and in (0, 1]")
        return self


class QuestionDecompositionDecision(StableModel):
    """Auditable disposition for every accepted candidate input."""

    candidate_artifact_id: str
    disposition: SubquestionDisposition
    subquestion_artifact_id: str | None
    matched_artifact_id: str | None
    lexical_overlap: float
    reason: str

    @field_validator(
        "candidate_artifact_id", "subquestion_artifact_id", "matched_artifact_id"
    )
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_decision(self) -> Self:
        if not math.isfinite(self.lexical_overlap) or not (
            0.0 <= self.lexical_overlap <= 1.0
        ):
            raise ValueError("lexical overlap must be finite and in [0, 1]")
        if not self.reason:
            raise ValueError("decomposition decisions require a reason")
        if self.disposition is SubquestionDisposition.selected:
            if self.subquestion_artifact_id is None or self.matched_artifact_id:
                raise ValueError(
                    "selected candidates require only a subquestion identity"
                )
        elif self.subquestion_artifact_id is not None:
            raise ValueError("rejected candidates cannot expose a subquestion identity")
        if self.disposition in {
            SubquestionDisposition.duplicate,
            SubquestionDisposition.overlap,
        }:
            if self.matched_artifact_id is None:
                raise ValueError("duplicate and overlap decisions require a match")
        elif self.matched_artifact_id is not None:
            raise ValueError("only duplicate and overlap decisions may name a match")
        return self


class QuestionDecompositionResult(StableModel):
    """Content-addressed bounded decomposition and complete decision record."""

    schema_version: Literal["bijux.canon.reason.question_decomposition.v1"]
    artifact_id: str
    root_question_artifact_id: str
    policy: QuestionDecompositionPolicy
    subquestions: tuple[ResearchSubquestion, ...]
    decisions: tuple[QuestionDecompositionDecision, ...]

    @field_validator("artifact_id", "root_question_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_result(self) -> Self:
        selected = tuple(
            decision.subquestion_artifact_id
            for decision in self.decisions
            if decision.disposition is SubquestionDisposition.selected
        )
        if selected != tuple(item.artifact_id for item in self.subquestions):
            raise ValueError("selected decisions must close every subquestion in order")
        if len(self.subquestions) > self.policy.max_subquestions:
            raise ValueError("decomposition exceeds the subquestion budget")
        if len(self.decisions) > self.policy.max_candidates:
            raise ValueError("decomposition exceeds the candidate budget")
        candidate_ids = tuple(item.candidate_artifact_id for item in self.decisions)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(
                "decomposition decisions require unique candidate identities"
            )
        if len({item.artifact_id for item in self.subquestions}) != len(
            self.subquestions
        ):
            raise ValueError("decomposition contains duplicate subquestion identities")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError(
                "question decomposition identity does not match its payload"
            )
        return self


class QuestionDecomposer:
    """Convert candidate data into bounded, non-overlapping subquestions."""

    def __init__(self, policy: QuestionDecompositionPolicy | None = None) -> None:
        self.policy = policy or QuestionDecompositionPolicy()

    def decompose(
        self,
        question: ResearchQuestion,
        candidates: tuple[SubquestionCandidate, ...],
    ) -> QuestionDecompositionResult:
        """Admit answerable candidates by priority with complete rejection reasons."""

        if len(question.text) > self.policy.max_question_characters:
            raise QuestionDecompositionError(
                QuestionDecompositionErrorCode.root_question_too_long,
                "root question exceeds the configured character budget",
            )
        if len(candidates) > self.policy.max_candidates:
            raise QuestionDecompositionError(
                QuestionDecompositionErrorCode.candidate_budget_exceeded,
                "candidate count exceeds the configured decomposition budget",
            )
        identities = tuple(candidate.artifact_id for candidate in candidates)
        if len(identities) != len(set(identities)):
            raise QuestionDecompositionError(
                QuestionDecompositionErrorCode.duplicate_candidate_identity,
                "candidate identities must be unique so every decision is auditable",
            )
        if any(
            len(candidate.evidence_needs) > self.policy.max_evidence_needs
            for candidate in candidates
        ):
            raise QuestionDecompositionError(
                QuestionDecompositionErrorCode.evidence_need_budget_exceeded,
                "a candidate exceeds the configured evidence-need budget",
            )

        ordered = sorted(
            candidates,
            key=lambda candidate: (-candidate.priority, candidate.artifact_id),
        )
        root_signature = _signature(question.text)
        selected: list[tuple[SubquestionCandidate, ResearchSubquestion]] = []
        decisions: list[QuestionDecompositionDecision] = []
        for candidate in ordered:
            signature = _signature(candidate.text)
            answerable = _is_answerable(
                candidate.text,
                signature,
                minimum=self.policy.min_content_tokens,
            )
            if not answerable:
                decisions.append(
                    _decision(
                        candidate,
                        SubquestionDisposition.unanswerable,
                        overlap=0.0,
                        reason="candidate is not phrased as a bounded answerable question",
                    )
                )
                continue
            if (
                candidate.scope_artifact_id == question.scope_artifact_id
                and signature == root_signature
            ):
                decisions.append(
                    _decision(
                        candidate,
                        SubquestionDisposition.duplicate,
                        matched_artifact_id=question.artifact_id,
                        overlap=1.0,
                        reason="candidate duplicates the root question in the same scope",
                    )
                )
                continue

            matched: tuple[ResearchSubquestion, float, bool] | None = None
            for admitted, subquestion in selected:
                if admitted.scope_artifact_id != candidate.scope_artifact_id:
                    continue
                admitted_signature = _signature(admitted.text)
                overlap = _lexical_overlap(signature, admitted_signature)
                duplicate = signature == admitted_signature
                if duplicate or overlap >= self.policy.overlap_threshold:
                    matched = (subquestion, overlap, duplicate)
                    break
            if matched is not None:
                subquestion, overlap, duplicate = matched
                disposition = (
                    SubquestionDisposition.duplicate
                    if duplicate
                    else SubquestionDisposition.overlap
                )
                decisions.append(
                    _decision(
                        candidate,
                        disposition,
                        matched_artifact_id=subquestion.artifact_id,
                        overlap=overlap,
                        reason=(
                            "candidate duplicates an admitted subquestion"
                            if duplicate
                            else "candidate exceeds the semantic-overlap threshold"
                        ),
                    )
                )
                continue
            if len(selected) >= self.policy.max_subquestions:
                decisions.append(
                    _decision(
                        candidate,
                        SubquestionDisposition.subquestion_budget,
                        overlap=0.0,
                        reason="candidate falls beyond the configured subquestion budget",
                    )
                )
                continue

            subquestion = _admit(question, candidate)
            selected.append((candidate, subquestion))
            decisions.append(
                _decision(
                    candidate,
                    SubquestionDisposition.selected,
                    subquestion_artifact_id=subquestion.artifact_id,
                    overlap=0.0,
                    reason="candidate is answerable, scoped, distinct, and within budget",
                )
            )

        payload = {
            "schema_version": "bijux.canon.reason.question_decomposition.v1",
            "root_question_artifact_id": question.artifact_id,
            "policy": self.policy.model_dump(mode="json"),
            "subquestions": tuple(
                subquestion.model_dump(mode="json") for _, subquestion in selected
            ),
            "decisions": tuple(
                decision.model_dump(mode="json") for decision in decisions
            ),
        }
        return QuestionDecompositionResult(
            artifact_id=content_artifact_id(payload),
            root_question_artifact_id=question.artifact_id,
            policy=self.policy,
            subquestions=tuple(subquestion for _, subquestion in selected),
            decisions=tuple(decisions),
            schema_version="bijux.canon.reason.question_decomposition.v1",
        )


def create_subquestion_candidate(
    *,
    text: str,
    scope_artifact_id: str,
    rationale: str,
    evidence_needs: tuple[str, ...],
    priority: int,
) -> SubquestionCandidate:
    """Create immutable candidate data with normalized text and stable identity."""

    normalized_text = _normalize_text(text)
    normalized_rationale = _normalize_text(rationale)
    normalized_needs = tuple(_normalize_text(item) for item in evidence_needs)
    payload = {
        "schema_version": "bijux.canon.reason.subquestion_candidate.v1",
        "text": normalized_text,
        "text_sha256": _sha256(normalized_text),
        "scope_artifact_id": scope_artifact_id,
        "rationale": normalized_rationale,
        "evidence_needs": normalized_needs,
        "priority": priority,
    }
    return SubquestionCandidate(
        schema_version="bijux.canon.reason.subquestion_candidate.v1",
        artifact_id=content_artifact_id(payload),
        text=normalized_text,
        text_sha256=_sha256(normalized_text),
        scope_artifact_id=scope_artifact_id,
        rationale=normalized_rationale,
        evidence_needs=normalized_needs,
        priority=priority,
    )


def _admit(
    question: ResearchQuestion, candidate: SubquestionCandidate
) -> ResearchSubquestion:
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.research_subquestion",
        "parent_question_artifact_id": question.artifact_id,
        "text": candidate.text,
        "text_sha256": candidate.text_sha256,
        "scope_artifact_id": candidate.scope_artifact_id,
        "rationale": candidate.rationale,
        "evidence_needs": candidate.evidence_needs,
        "priority": candidate.priority,
        "status": SubquestionStatus.pending.value,
    }
    return ResearchSubquestion(
        artifact_id=content_artifact_id(payload),
        parent_question_artifact_id=question.artifact_id,
        text=candidate.text,
        text_sha256=candidate.text_sha256,
        scope_artifact_id=candidate.scope_artifact_id,
        rationale=candidate.rationale,
        evidence_needs=candidate.evidence_needs,
        priority=candidate.priority,
        status=SubquestionStatus.pending,
    )


def _decision(
    candidate: SubquestionCandidate,
    disposition: SubquestionDisposition,
    *,
    overlap: float,
    reason: str,
    subquestion_artifact_id: str | None = None,
    matched_artifact_id: str | None = None,
) -> QuestionDecompositionDecision:
    return QuestionDecompositionDecision(
        candidate_artifact_id=candidate.artifact_id,
        disposition=disposition,
        subquestion_artifact_id=subquestion_artifact_id,
        matched_artifact_id=matched_artifact_id,
        lexical_overlap=round(overlap, 12),
        reason=reason,
    )


def _normalize_text(value: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFC", value).strip())


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _signature(value: str) -> tuple[str, ...]:
    tokens = tuple(token.casefold() for token in _WORD.findall(value))
    content = tuple(token for token in tokens if token not in _SIGNATURE_STOP_WORDS)
    return content or tokens


def _lexical_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return (2.0 * len(left_set & right_set)) / (len(left_set) + len(right_set))


def _is_answerable(text: str, signature: tuple[str, ...], *, minimum: int) -> bool:
    tokens = tuple(token.casefold() for token in _WORD.findall(text))
    if len(set(signature)) < minimum or not tokens:
        return False
    return text.endswith("?") or tokens[0] in _QUESTION_OPENERS


__all__ = [
    "QuestionDecomposer",
    "QuestionDecompositionDecision",
    "QuestionDecompositionError",
    "QuestionDecompositionErrorCode",
    "QuestionDecompositionPolicy",
    "QuestionDecompositionResult",
    "ResearchQuestion",
    "ResearchQuestionIntent",
    "ResearchSubquestion",
    "SubquestionCandidate",
    "SubquestionDisposition",
    "SubquestionStatus",
    "create_subquestion_candidate",
]
