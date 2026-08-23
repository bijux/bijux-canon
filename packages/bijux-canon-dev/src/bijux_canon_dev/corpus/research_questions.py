#!/usr/bin/env python3
"""Validate diverse semantic research questions against immutable qrel evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from datetime import date
import json
from pathlib import Path
import re
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_qrels import (
    ADJUDICATOR_ID,
    load_qrels,
    qrel_identity,
)

SCHEMA_VERSION = "bijux.canon.research_question.v1"
REVIEWER_ID = "bijux-corpus-curation-secondary"
REVIEW_STATUS = "independent_source_review_complete"
REVIEW_METHOD = "independent source-first semantic question and evidence adjudication"
CATEGORIES = frozenset(
    {
        "ambiguous",
        "conflict",
        "cross-paper-synthesis",
        "finding",
        "limitation",
        "method",
        "multi-hop",
        "out-of-scope",
        "population-context",
    }
)
ANSWERABILITY = {
    "answerable": (False, "answer"),
    "qualified": (False, "qualified-answer"),
    "ambiguous": (True, "clarification-required"),
    "out-of-scope": (True, "abstain"),
}
EVIDENCE_RELATIONS = frozenset({"contextualizes", "limits", "opposes", "supports"})
_WORD = re.compile(r"[\w-]+", re.UNICODE)


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load canonical questions from a regular, non-symlink JSONL file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"research questions are not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank research question line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(f"non-canonical research question line: {line_number}")
        records.append(value)
    return records


def _question_terms(question: str) -> frozenset[str]:
    return frozenset(term.casefold() for term in _WORD.findall(question))


def _validate_question_texts(records: list[dict[str, Any]]) -> None:
    normalized: dict[str, str] = {}
    term_sets: list[tuple[str, frozenset[str]]] = []
    for record in records:
        question_id = str(record.get("question_id"))
        question = record.get("question")
        if (
            not isinstance(question, str)
            or len(question) < 24
            or not question.endswith("?")
        ):
            raise RuntimeError(f"invalid research question text: {question_id}")
        key = " ".join(question.casefold().split())
        if key in normalized:
            raise RuntimeError(
                f"duplicate research question text: {normalized[key]}, {question_id}"
            )
        normalized[key] = question_id
        terms = _question_terms(question)
        for prior_id, prior_terms in term_sets:
            union = terms | prior_terms
            similarity = len(terms & prior_terms) / len(union) if union else 1.0
            if similarity >= 0.8:
                raise RuntimeError(
                    f"research question paraphrase pair: {prior_id}, {question_id}"
                )
        term_sets.append((question_id, terms))


def validate_questions(
    records: list[dict[str, Any]], *, qrels_path: Path
) -> dict[str, Any]:
    """Validate question diversity, review lineage, and exact evidence reachability."""

    qrels = {str(record["qrel_id"]): record for record in load_qrels(qrels_path)}
    question_ids: set[str] = set()
    categories: Counter[str] = Counter()
    answerability: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    relevance_grades: Counter[str] = Counter()
    source_ids: set[str] = set()
    evidence_ids: set[str] = set()
    _validate_question_texts(records)

    for record in records:
        question_id = record.get("question_id")
        category = record.get("category")
        disposition = record.get("answerability")
        if (
            not isinstance(question_id, str)
            or not question_id.startswith("adna-")
            or question_id in question_ids
            or category not in CATEGORIES
            or disposition not in ANSWERABILITY
        ):
            raise RuntimeError(f"invalid research question identity: {question_id}")
        question_ids.add(question_id)
        categories[str(category)] += 1
        answerability[str(disposition)] += 1
        expected_abstention, expected_disposition = ANSWERABILITY[str(disposition)]
        required = {
            "abstention_expected": expected_abstention,
            "expected_disposition": expected_disposition,
            "review_method": REVIEW_METHOD,
            "review_status": REVIEW_STATUS,
            "reviewer_id": REVIEWER_ID,
            "schema_version": SCHEMA_VERSION,
            "system_output_consulted": False,
            "system_output_may_define_truth": False,
        }
        drift = [key for key, value in required.items() if record.get(key) != value]
        if drift:
            raise RuntimeError(
                f"research question metadata drift: {question_id}: {drift}"
            )
        if record["reviewer_id"] == ADJUDICATOR_ID:
            raise RuntimeError("question review is not independent of primary qrels")
        try:
            date.fromisoformat(record["reviewed_on"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"invalid question review date: {question_id}"
            ) from error
        rationale = record.get("rationale")
        points = record.get("acceptable_answer_points")
        if (
            not isinstance(rationale, str)
            or len(rationale) < 60
            or not isinstance(points, list)
            or not points
            or any(not isinstance(point, str) or len(point) < 20 for point in points)
        ):
            raise RuntimeError(f"incomplete research question truth: {question_id}")
        evidence = record.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise RuntimeError(f"missing research question evidence: {question_id}")
        question_sources: set[str] = set()
        question_evidence: set[str] = set()
        for item in evidence:
            if not isinstance(item, Mapping):
                raise RuntimeError(f"invalid question evidence: {question_id}")
            qrel_id = item.get("qrel_id")
            relation = item.get("relation")
            evidence_rationale = item.get("rationale")
            relevance_grade = item.get("relevance_grade")
            qrel = qrels.get(str(qrel_id))
            if (
                qrel is None
                or relation not in EVIDENCE_RELATIONS
                or not isinstance(evidence_rationale, str)
                or len(evidence_rationale) < 40
                or not isinstance(relevance_grade, int)
                or isinstance(relevance_grade, bool)
                or relevance_grade not in {1, 2, 3}
                or qrel_id in question_evidence
            ):
                raise RuntimeError(
                    f"invalid question evidence: {question_id}: {qrel_id}"
                )
            if qrel.get("qrel_identity_sha256") != qrel_identity(qrel):
                raise RuntimeError(
                    f"question evidence identity mismatch: {question_id}: {qrel_id}"
                )
            question_evidence.add(str(qrel_id))
            evidence_ids.add(str(qrel_id))
            relations[str(relation)] += 1
            relevance_grades[str(relevance_grade)] += 1
            source_id = str(qrel["source_id"])
            question_sources.add(source_id)
            source_ids.add(source_id)
            chunk = qrel.get("chunk")
            if not isinstance(chunk, Mapping) or not isinstance(
                chunk.get("chunk_id"), str
            ):
                raise RuntimeError(
                    f"detached question evidence: {question_id}: {qrel_id}"
                )
        if (
            category in {"conflict", "cross-paper-synthesis", "multi-hop"}
            and len(question_sources) < 2
        ):
            raise RuntimeError(
                f"question category requires multiple sources: {question_id}"
            )

    if set(categories) != CATEGORIES or any(count < 2 for count in categories.values()):
        raise RuntimeError("research question category balance mismatch")
    if set(relations) != EVIDENCE_RELATIONS:
        raise RuntimeError("research question evidence relation coverage mismatch")
    if set(answerability) != set(ANSWERABILITY):
        raise RuntimeError("research question answerability coverage mismatch")
    return {
        "answerability_counts": dict(sorted(answerability.items())),
        "category_counts": dict(sorted(categories.items())),
        "evidence_qrel_count": len(evidence_ids),
        "evidence_relevance_grade_counts": dict(sorted(relevance_grades.items())),
        "evidence_relation_counts": dict(sorted(relations.items())),
        "question_count": len(records),
        "question_set_sha256": sha256(
            b"".join(canonical(record) + b"\n" for record in records)
        ),
        "reviewer_id": REVIEWER_ID,
        "source_count": len(source_ids),
    }


def main() -> None:
    """Validate and summarize the durable semantic research questions."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()
    json.dump(
        validate_questions(load_questions(args.questions), qrels_path=args.qrels),
        sys.stdout,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
