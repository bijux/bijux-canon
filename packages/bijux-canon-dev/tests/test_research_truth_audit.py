"""Semantic population and provenance audits for ancient-DNA truth."""

from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_dev.corpus.research_truth_audit import audit_research_truth

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"


def _audit() -> dict[str, object]:
    return audit_research_truth(
        cases_path=TRUTH_ROOT / "evaluation-cases.jsonl",
        claim_truth_path=TRUTH_ROOT / "claim-truth.jsonl",
        question_claim_truth_path=TRUTH_ROOT / "question-claim-truth.jsonl",
        qrels_path=TRUTH_ROOT / "qrels.jsonl",
        questions_path=TRUTH_ROOT / "research-questions.jsonl",
        split_path=TRUTH_ROOT / "split.json",
    )


def test_audit_reports_questions_instead_of_cross_product_rows() -> None:
    report = _audit()
    assert report["inventory"] == {
        "case_row_count": 18,
        "legacy_qrel_query_count": 8,
        "legacy_qrel_query_text_count": 8,
        "reviewed_semantic_question_count": 18,
        "reviewed_semantic_question_text_count": 18,
        "source_count": 8,
        "unique_case_count": 18,
        "unique_claim_count": 32,
        "unique_claim_identity_count": 32,
        "unique_qrel_count": 30,
    }
    assert len(report["question_inventory"]) == 18
    assert len(report["legacy_query_inventory"]) == 8
    assert len(report["qrel_inventory"]) == 30
    assert len(report["claim_inventory"]) == 32
    assert report["case_label_disposition_counts"] == {
        "development-labels-visible": 12,
        "heldout-labels-sealed": 6,
    }
    consistency = report["dataset_consistency"]
    assert isinstance(consistency, dict)
    assert all(consistency.values())


def test_audit_discloses_review_lineage_and_family_partition() -> None:
    report = _audit()
    provenance = report["review_provenance"]
    partition = report["partition"]
    assert isinstance(provenance, dict)
    assert isinstance(partition, dict)

    assert provenance["independent_legacy_truth_review_complete"] is False
    assert provenance["label_status"] == (
        "semantic-questions-independent-legacy-truth-review-required"
    )
    qrels = provenance["qrels"]
    claims = provenance["claims"]
    questions = provenance["questions"]
    assert isinstance(qrels, dict) and isinstance(claims, dict)
    assert isinstance(questions, dict)
    assert qrels["reviewer_ids"] == ["bijux-corpus-curation-primary"]
    assert claims["reviewer_ids"] == ["bijux-corpus-curation-primary"]
    assert questions["reviewer_ids"] == ["bijux-corpus-curation-secondary"]
    assert questions["system_output_consulted"] == [False]

    assert partition["leakage_free"] is True
    assert partition["development"] == {
        "case_count": 12,
        "family_count": 3,
        "question_count": 12,
    }
    assert partition["heldout"] == {
        "case_count": 6,
        "family_count": 1,
        "question_count": 6,
    }
    assert partition["overlap"] == {
        "case_count": 0,
        "family_count": 0,
        "question_count": 0,
    }
    queue = report["review_queue"]
    assert isinstance(queue, list)
    assert [item["issue_id"] for item in queue] == ["independent-review-required"]
    assert report["release_eligible"] is False


def test_audit_is_restart_stable_and_canonically_identified() -> None:
    first = _audit()
    second = _audit()

    assert first == second
    assert first["schema_version"] == "bijux.canon.research_truth_audit.v4"
    assert first["audit_identity_sha256"] == second["audit_identity_sha256"]
    assert len(str(first["audit_identity_sha256"])) == 64
    json.dumps(first, sort_keys=True)
