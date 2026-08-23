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
        qrels_path=TRUTH_ROOT / "qrels.jsonl",
        questions_path=TRUTH_ROOT / "research-questions.jsonl",
        split_path=TRUTH_ROOT / "split.json",
    )


def test_audit_reports_semantic_populations_instead_of_row_denominators() -> None:
    report = _audit()
    inventory = report["inventory"]
    assert isinstance(inventory, dict)

    assert inventory == {
        "case_row_count": 120,
        "reviewed_semantic_question_count": 18,
        "reviewed_semantic_question_text_count": 18,
        "source_count": 8,
        "unique_case_count": 120,
        "unique_claim_count": 32,
        "unique_claim_identity_count": 32,
        "unique_qrel_claim_pair_count": 120,
        "unique_qrel_count": 30,
        "unique_query_count": 8,
        "unique_query_text_count": 8,
    }
    assert report["claim_class_counts"] == {
        "expected": 8,
        "forbidden": 8,
        "opposed": 8,
        "optional": 8,
    }
    assert report["case_answerability_counts"] == {
        "answerable": 16,
        "must-abstain": 104,
    }
    assert len(report["query_inventory"]) == 8
    assert len(report["reviewed_question_inventory"]) == 18
    assert report["reviewed_question_category_counts"] == {
        "ambiguous": 2,
        "conflict": 2,
        "cross-paper-synthesis": 2,
        "finding": 2,
        "limitation": 2,
        "method": 2,
        "multi-hop": 2,
        "out-of-scope": 2,
        "population-context": 2,
    }
    assert len(report["qrel_inventory"]) == 30
    assert len(report["claim_inventory"]) == 32
    assert report["qrel_relevance_grade_counts"] == {"1": 14, "2": 8, "3": 8}
    assert report["case_label_counts"] == {
        "citation_relation": {
            "insufficient": 88,
            "limits": 8,
            "opposes": 8,
            "supports": 16,
        },
        "difficulty": {"adversarial": 30, "hard": 74, "standard": 16},
        "negative": {"false": 24, "true": 96},
        "split": {"development": 80, "heldout": 40},
    }
    consistency = report["dataset_consistency"]
    assert isinstance(consistency, dict)
    assert all(consistency.values())


def test_audit_discloses_review_lineage_and_partition_leakage() -> None:
    report = _audit()
    provenance = report["review_provenance"]
    partition = report["partition"]
    assert isinstance(provenance, dict)
    assert isinstance(partition, dict)

    assert provenance["independent_review_complete"] is False
    assert provenance["label_status"] == (
        "primary-reviewed-independent-review-required"
    )
    qrels = provenance["qrels"]
    claims = provenance["claims"]
    questions = provenance["questions"]
    assert isinstance(qrels, dict) and isinstance(claims, dict)
    assert isinstance(questions, dict)
    assert qrels["reviewer_ids"] == ["bijux-corpus-curation-primary"]
    assert claims["reviewer_ids"] == ["bijux-corpus-curation-primary"]
    assert qrels["system_output_consulted"] == [False]
    assert qrels["system_output_consulted_declared"] is True
    assert claims["system_output_consulted"] == []
    assert claims["system_output_consulted_declared"] is False
    assert questions["reviewer_ids"] == ["bijux-corpus-curation-secondary"]
    assert questions["system_output_consulted"] == [False]
    assert questions["system_output_consulted_declared"] is True

    assert partition["leakage_free"] is False
    assert partition["overlap"] == {
        "case_count": 0,
        "claim_count": 32,
        "qrel_count": 27,
        "query_count": 8,
    }
    queue = report["review_queue"]
    assert isinstance(queue, list)
    assert [item["issue_id"] for item in queue] == [
        "independent-review-required",
        "query-split-leakage",
        "qrel-split-leakage",
        "claim-split-leakage",
    ]
    assert report["release_eligible"] is False


def test_audit_is_restart_stable_and_canonically_identified() -> None:
    first = _audit()
    second = _audit()

    assert first == second
    assert first["audit_identity_sha256"] == second["audit_identity_sha256"]
    assert len(str(first["audit_identity_sha256"])) == 64
    json.dumps(first, sort_keys=True)
