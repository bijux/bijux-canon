# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for hash-bound held-out evaluation isolation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_reason.evaluation import (
    EvaluationAccessPurpose,
    EvaluationPartitionIdentities,
    EvaluationSplit,
    HeldoutIsolationError,
    HeldoutIsolationLedger,
    HeldoutIsolationReport,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
SPLIT_PATH = REPO_ROOT / "examples/ancient-dna-research/truth/split.json"


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _identities() -> EvaluationPartitionIdentities:
    rows = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["cases"]
    partitions: dict[str, tuple[list[object], list[object]]] = {
        "development": ([], []),
        "heldout": ([], []),
    }
    for row in rows:
        inputs, labels = partitions[row["split"]]
        inputs.append(
            {
                key: value
                for key, value in row.items()
                if key
                not in {
                    "case_identity_sha256",
                    "partition_review_sha256",
                    "question_label_sha256",
                }
            }
        )
        labels.append(
            {
                "case_id": row["case_id"],
                "partition_review_sha256": row["partition_review_sha256"],
                "question_label_sha256": row["question_label_sha256"],
            }
        )
    development_inputs, development_labels = partitions["development"]
    heldout_inputs, heldout_labels = partitions["heldout"]
    return EvaluationPartitionIdentities(
        development_inputs_sha256=_sha256(development_inputs),
        development_labels_sha256=_sha256(development_labels),
        heldout_inputs_sha256=_sha256(heldout_inputs),
        heldout_labels_sha256=_sha256(heldout_labels),
    )


def test_real_partition_access_and_result_identities_survive_restart() -> None:
    identities = _identities()
    ledger = HeldoutIsolationLedger(identities)
    ledger.authorize(
        access_id="development-tuning",
        split=EvaluationSplit.development,
        purpose=EvaluationAccessPurpose.tuning,
        labels_requested=True,
    )
    heldout = ledger.authorize(
        access_id="heldout-evaluation",
        split=EvaluationSplit.heldout,
        purpose=EvaluationAccessPurpose.evaluation,
        labels_requested=True,
    )
    ledger.record_result(
        access_artifact_id=heldout.artifact_id,
        result_sha256=_sha256({"report": "heldout-result"}),
    )

    report = ledger.report()
    restarted = HeldoutIsolationReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.accesses[1].inputs_sha256 == identities.heldout_inputs_sha256
    assert report.accesses[1].labels_sha256 == identities.heldout_labels_sha256
    assert report.results[0].access_artifact_id == heldout.artifact_id


@pytest.mark.parametrize(
    "purpose",
    [
        EvaluationAccessPurpose.tuning,
        EvaluationAccessPurpose.configuration,
        EvaluationAccessPurpose.prompt_selection,
    ],
)
def test_heldout_partition_refuses_non_evaluation_access(
    purpose: EvaluationAccessPurpose,
) -> None:
    ledger = HeldoutIsolationLedger(_identities())

    with pytest.raises(HeldoutIsolationError, match="cannot be used"):
        ledger.authorize(
            access_id=f"forbidden-{purpose.value}",
            split=EvaluationSplit.heldout,
            purpose=purpose,
            labels_requested=False,
        )

    assert ledger.report().accesses == ()


def test_unrecorded_evaluation_result_keeps_ledger_failed() -> None:
    ledger = HeldoutIsolationLedger(_identities())
    ledger.authorize(
        access_id="incomplete-heldout-evaluation",
        split=EvaluationSplit.heldout,
        purpose=EvaluationAccessPurpose.evaluation,
        labels_requested=False,
    )

    report = ledger.report()

    assert not report.passed
    assert len(report.accesses) == 1
    assert report.results == ()
