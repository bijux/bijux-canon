"""Independent human review controls for release truth."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import cast

import pytest

from bijux_canon_dev.corpus.research_truth_review import (
    TruthReviewError,
    admit_truth_reviews,
    create_truth_review_packet,
    seal_truth_adjudication,
    seal_truth_review,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
TRUTH_ROOT = RESEARCH_ROOT / "truth"
PROTOCOL = REPO_ROOT / "docs/04-bijux-canon-reason/quality/annotation-protocol.md"


def _packet(directory: Path) -> dict[str, object]:
    return create_truth_review_packet(
        truth_root=TRUTH_ROOT,
        corpus_lock_path=RESEARCH_ROOT / "corpus.lock.json",
        research_root=RESEARCH_ROOT,
        protocol_path=PROTOCOL,
        source_commit="a" * 40,
        output_directory=directory,
    )


def _draft(packet: Path, reviewer_id: str) -> dict[str, object]:
    value = json.loads((packet / "review-template.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value["reviewer_id"] = reviewer_id
    value["reviewed_on"] = "2026-08-25"
    for decision in cast(list[dict[str, object]], value["decisions"]):
        decision["verdict"] = "approve"
        decision["rationale"] = "Verified directly against the packet source material."
    return value


def _seal(packet: Path, reviewer_id: str) -> dict[str, object]:
    return seal_truth_review(
        packet_directory=packet,
        draft=_draft(packet, reviewer_id),
    )


def test_packet_is_complete_blind_portable_and_restart_stable(tmp_path: Path) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first = _packet(first_directory)
    second = _packet(second_directory)

    assert first == second
    assert first["subject_count"] == 142
    assert first["subject_counts"] == {
        "claim": 32,
        "evaluation-case": 18,
        "locator": 32,
        "qrel": 30,
        "question": 18,
        "question-claim": 12,
    }
    assert first["system_output_included"] is False
    assert len(list((first_directory / "sources").iterdir())) == 8
    packet_text = (first_directory / "subjects.jsonl").read_text(encoding="utf-8")
    assert "bijux-corpus-curation-primary" not in packet_text
    assert "bijux-corpus-curation-secondary" not in packet_text
    assert "bijux-production-source-review" not in packet_text
    assert (first_directory / "protocol.md").read_bytes() == PROTOCOL.read_bytes()


def test_two_distinct_source_first_reviews_admit_complete_truth(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    _packet(packet)
    first = _seal(packet, "independent-reviewer-a")
    second = _seal(packet, "independent-reviewer-b")

    report = admit_truth_reviews(
        packet_directory=packet,
        reviews=[first, second],
    )

    assert report["admitted_subject_count"] == 142
    assert report["required_subject_count"] == 142
    assert report["disagreement_subject_ids"] == []
    assert report["correction_required_subject_ids"] == []
    assert report["release_eligible"] is True
    assert report["manual_signoff_verified"] is True
    assert report["system_output_consulted"] is False


def test_review_rejects_prior_reviewer_system_output_and_packet_tamper(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet"
    _packet(packet)
    prior = _seal(packet, "bijux-corpus-curation-primary")
    independent = _seal(packet, "independent-reviewer-b")
    with pytest.raises(TruthReviewError, match="prior reviewer"):
        admit_truth_reviews(packet_directory=packet, reviews=[prior, independent])

    consulted = _draft(packet, "independent-reviewer-c")
    consulted["system_output_consulted"] = True
    with pytest.raises(TruthReviewError, match="policy"):
        seal_truth_review(packet_directory=packet, draft=consulted)

    subjects = packet / "subjects.jsonl"
    subjects.write_bytes(subjects.read_bytes() + b"\n")
    with pytest.raises(TruthReviewError, match="subjects digest"):
        _seal(packet, "independent-reviewer-d")


def test_review_identity_tamper_and_duplicate_reviewer_fail_closed(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet"
    _packet(packet)
    first = _seal(packet, "independent-reviewer-a")
    duplicate = _seal(packet, "independent-reviewer-a")
    with pytest.raises(TruthReviewError, match="distinct"):
        admit_truth_reviews(packet_directory=packet, reviews=[first, duplicate])

    tampered = deepcopy(first)
    cast(list[dict[str, object]], tampered["decisions"])[0]["rationale"] = "Changed"
    with pytest.raises(TruthReviewError, match="identity mismatch"):
        admit_truth_reviews(packet_directory=packet, reviews=[tampered, duplicate])


def test_disagreement_requires_independent_adjudication_and_new_packet_for_change(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "packet"
    manifest = _packet(packet)
    first = _seal(packet, "independent-reviewer-a")
    changed_draft = _draft(packet, "independent-reviewer-b")
    changed = cast(list[dict[str, object]], changed_draft["decisions"])[0]
    changed["verdict"] = "changes-required"
    changed["rationale"] = "The source requires a narrower claim boundary."
    changed["conflicts"] = ["scope-overstatement"]
    changed["proposed_correction"] = {"replacement": "narrower reviewed value"}
    second = seal_truth_review(packet_directory=packet, draft=changed_draft)

    with pytest.raises(TruthReviewError, match="requires adjudication"):
        admit_truth_reviews(packet_directory=packet, reviews=[first, second])

    subject_id = str(changed["subject_id"])
    adjudication = seal_truth_adjudication(
        packet_directory=packet,
        reviews=[first, second],
        draft={
            "schema_version": "bijux.canon.research_truth_adjudication.v1",
            "packet_id": manifest["packet_id"],
            "adjudicator_id": "independent-adjudicator",
            "adjudicated_on": "2026-08-25",
            "review_ids": [first["review_id"], second["review_id"]],
            "source_material_reviewed": True,
            "system_output_consulted": False,
            "decisions": [
                {
                    "subject_id": subject_id,
                    "verdict": "admit",
                    "rationale": "The correction is source-grounded and must be applied.",
                    "resolved_conflict_ids": ["scope-overstatement"],
                }
            ],
        },
    )
    report = admit_truth_reviews(
        packet_directory=packet,
        reviews=[first, second],
        adjudication=adjudication,
    )

    assert report["disagreement_subject_ids"] == [subject_id]
    assert report["correction_required_subject_ids"] == [subject_id]
    assert report["release_eligible"] is False
    assert report["manual_signoff_verified"] is False


def test_adjudicator_must_be_distinct_and_cover_exact_issue_set(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    manifest = _packet(packet)
    first = _seal(packet, "independent-reviewer-a")
    draft = _draft(packet, "independent-reviewer-b")
    changed = cast(list[dict[str, object]], draft["decisions"])[0]
    changed["verdict"] = "reject"
    changed["rationale"] = "The proposed record is not supported by its source."
    changed["conflicts"] = ["unsupported-record"]
    second = seal_truth_review(packet_directory=packet, draft=draft)
    adjudication = {
        "schema_version": "bijux.canon.research_truth_adjudication.v1",
        "packet_id": manifest["packet_id"],
        "adjudicator_id": "independent-reviewer-a",
        "adjudicated_on": "2026-08-25",
        "review_ids": [first["review_id"], second["review_id"]],
        "source_material_reviewed": True,
        "system_output_consulted": False,
        "decisions": [],
    }
    with pytest.raises(TruthReviewError, match="policy"):
        seal_truth_adjudication(
            packet_directory=packet,
            reviews=[first, second],
            draft=adjudication,
        )
