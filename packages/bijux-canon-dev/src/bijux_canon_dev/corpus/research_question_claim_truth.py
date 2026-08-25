#!/usr/bin/env python3
"""Validate semantic answer points and their exact reviewed evidence relations."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_qrels import load_qrels, qrel_identity
from bijux_canon_dev.corpus.research_questions import (
    load_questions,
    validate_questions,
)

SCHEMA_VERSION = "bijux.canon.research_question_claim_truth.v1"
REVIEWER_ID = "bijux-production-source-review"
REVIEW_METHOD = (
    "source-first answer-point to exact-qrel semantic crosswalk without consulting "
    "system output"
)
CLAIM_ROLES = frozenset({"expected-answer", "abstention-reason"})
EVIDENCE_RELATIONS = frozenset({"insufficient", "limits", "opposes", "supports"})


def load_question_claim_truth(path: Path) -> list[dict[str, Any]]:
    """Load canonical question-claim truth from a regular JSONL file."""

    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"question-claim truth is not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            raise RuntimeError(f"blank question-claim truth line: {line_number}")
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(
                f"non-canonical question-claim truth line: {line_number}"
            )
        records.append(value)
    return records


def validate_question_claim_truth(
    records: list[dict[str, Any]],
    *,
    cases_path: Path,
    questions_path: Path,
    qrels_path: Path,
) -> dict[str, Any]:
    """Validate complete development-point coverage and exact qrel references."""

    questions = load_questions(questions_path)
    validate_questions(questions, qrels_path=qrels_path)
    questions_by_id = {str(item["question_id"]): item for item in questions}
    qrels = {str(item["qrel_id"]): item for item in load_qrels(qrels_path)}
    cases = _load_cases(cases_path)
    development = {
        str(item["question_id"]): item
        for item in cases
        if item.get("split") == "development"
    }
    seen_questions: set[str] = set()
    seen_cases: set[str] = set()
    seen_statements: set[str] = set()
    citation_count = 0

    for record in records:
        question_id = record.get("question_id")
        case_id = record.get("case_id")
        question = questions_by_id.get(str(question_id))
        if (
            not isinstance(question_id, str)
            or question_id not in development
            or question is None
            or question_id in seen_questions
            or not isinstance(case_id, str)
            or case_id != development[question_id].get("case_id")
            or case_id in seen_cases
        ):
            raise RuntimeError(f"invalid question-claim truth identity: {question_id}")
        seen_questions.add(question_id)
        seen_cases.add(case_id)
        required = {
            "review_method": REVIEW_METHOD,
            "reviewer_id": REVIEWER_ID,
            "schema_version": SCHEMA_VERSION,
            "system_output_consulted": False,
        }
        drift = [
            key for key, expected in required.items() if record.get(key) != expected
        ]
        if drift:
            raise RuntimeError(
                f"question-claim review metadata drift: {question_id}: {drift}"
            )
        try:
            date.fromisoformat(str(record["reviewed_on"]))
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"invalid question-claim review date: {question_id}"
            ) from error
        claims = record.get("claims")
        if not isinstance(claims, list) or not claims:
            raise RuntimeError(f"missing question-claim truth: {question_id}")
        expected_points = question["acceptable_answer_points"]
        if [item.get("statement") for item in claims] != expected_points:
            raise RuntimeError(
                f"question-claim statements differ from reviewed points: {question_id}"
            )
        expected_role = (
            "abstention-reason"
            if bool(question["abstention_expected"])
            else "expected-answer"
        )
        question_qrels = {str(item["qrel_id"]) for item in question.get("evidence", [])}
        for index, claim in enumerate(claims):
            statement = claim.get("statement")
            role = claim.get("claim_role")
            citations = claim.get("citations")
            if (
                not isinstance(statement, str)
                or statement in seen_statements
                or role not in CLAIM_ROLES
                or role != expected_role
                or not isinstance(citations, list)
                or not citations
            ):
                raise RuntimeError(
                    f"invalid reviewed question claim: {question_id}:{index}"
                )
            seen_statements.add(statement)
            cited_ids: set[str] = set()
            cited_relations: set[str] = set()
            for citation in citations:
                qrel_id = citation.get("qrel_id")
                relation = citation.get("relation")
                qrel = qrels.get(str(qrel_id))
                if (
                    not isinstance(qrel_id, str)
                    or qrel_id not in question_qrels
                    or qrel_id in cited_ids
                    or qrel is None
                    or qrel.get("qrel_identity_sha256") != qrel_identity(qrel)
                    or relation not in EVIDENCE_RELATIONS
                ):
                    raise RuntimeError(
                        f"invalid question-claim citation: {question_id}:{index}:{qrel_id}"
                    )
                cited_ids.add(qrel_id)
                cited_relations.add(str(relation))
                citation_count += 1
            if role == "expected-answer" and "supports" not in cited_relations:
                raise RuntimeError(
                    f"expected answer point lacks support: {question_id}:{index}"
                )
            if role == "abstention-reason" and not cited_relations.intersection(
                {"insufficient", "limits", "opposes"}
            ):
                raise RuntimeError(
                    f"abstention reason lacks limiting evidence: {question_id}:{index}"
                )

    if seen_questions != set(development):
        missing = sorted(set(development) - seen_questions)
        extra = sorted(seen_questions - set(development))
        raise RuntimeError(
            f"question-claim development population differs: missing={missing}, extra={extra}"
        )
    return {
        "case_count": len(records),
        "citation_relation_count": citation_count,
        "claim_count": len(seen_statements),
        "question_claim_set_sha256": sha256(
            b"".join(canonical(item) + b"\n" for item in records)
        ),
        "reviewer_id": REVIEWER_ID,
    }


def _load_cases(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"evaluation cases are not a regular file: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict) or canonical(value) != line:
            raise RuntimeError(f"non-canonical evaluation case line: {line_number}")
        records.append(value)
    return records


def main() -> None:
    """Validate and summarize reviewed semantic question-claim truth."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--question-claims", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()
    result = validate_question_claim_truth(
        load_question_claim_truth(args.question_claims),
        cases_path=args.cases,
        questions_path=args.questions,
        qrels_path=args.qrels,
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
