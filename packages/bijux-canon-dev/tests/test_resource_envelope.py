from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_dev.performance.resource_envelope import (
    _evaluate,
    _profile_metrics,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _exchange(evidence: Path, name: str, duration: float) -> None:
    (evidence / f"{name}.exchange.json").write_text(
        json.dumps({"duration_seconds": duration}), encoding="utf-8"
    )


def test_profile_metrics_cover_stages_memory_and_disk(tmp_path: Path) -> None:
    profile = tmp_path / "offline-lexical"
    evidence = profile / "evidence"
    index = profile / "runtime-workspace-restored" / "indexes"
    evidence.mkdir(parents=True)
    index.mkdir(parents=True)
    (index / "generation.bin").write_bytes(b"index")
    digest = "a" * 64
    payload = (
        profile
        / "runtime-workspace-restored"
        / "cas"
        / "objects"
        / "sha256"
        / "aa"
        / digest
        / "payload"
    )
    payload.parent.mkdir(parents=True)
    payload.write_bytes(b"lexical-index")
    (evidence / "summary.json").write_text(
        json.dumps({"index": {"artifact_id": f"sha256:{digest}"}}),
        encoding="utf-8",
    )
    for name, duration in (
        ("corpus-job", 2.0),
        ("lexical-index-job", 3.0),
        ("evidence-search-job", 4.0),
        ("grounded-answer-job", 5.0),
        ("corpus-inspection", 0.5),
        ("grounded-answer-inspection", 0.75),
    ):
        _exchange(evidence, name, duration)

    metrics = _profile_metrics(
        profile_id="offline-lexical",
        profile_root=profile,
        measurement={"peak_rss_bytes": 100, "wall_seconds": 20.0},
        startup={"wall_seconds": 0.25},
    )

    assert metrics["startup_seconds"] == 0.25
    assert metrics["ingest_seconds"] == 2.0
    assert metrics["index_seconds"] == 3.0
    assert metrics["query_seconds"] == 4.0
    assert metrics["answer_seconds"] == 5.0
    assert metrics["inspection_seconds"] == 1.25
    assert metrics["peak_rss_bytes"] == 100
    assert metrics["index_bytes"] == 13
    assert metrics["workspace_disk_bytes"] == 18
    assert metrics["profile_disk_bytes"] > metrics["workspace_disk_bytes"]


def test_ceiling_evaluation_reports_each_regression_without_hiding_it() -> None:
    observations = _evaluate(
        {"offline-lexical": {"total_seconds": 11.0, "peak_rss_bytes": 90}},
        {
            "profiles": {
                "offline-lexical": {
                    "total_seconds": 10.0,
                    "peak_rss_bytes": 100,
                }
            }
        },
    )

    assert observations == [
        {
            "ceiling": 10.0,
            "metric_id": "total_seconds",
            "observed": 11.0,
            "passed": False,
            "profile_id": "offline-lexical",
        },
        {
            "ceiling": 100,
            "metric_id": "peak_rss_bytes",
            "observed": 90,
            "passed": True,
            "profile_id": "offline-lexical",
        },
    ]


def test_checked_in_resource_ceilings_cover_every_required_measurement() -> None:
    ceilings = json.loads(
        (
            REPO_ROOT / "examples" / "ancient-dna-research" / "resource-ceilings.json"
        ).read_text(encoding="utf-8")
    )
    required = {
        "answer_seconds",
        "index_bytes",
        "index_seconds",
        "ingest_seconds",
        "inspection_seconds",
        "peak_rss_bytes",
        "profile_disk_bytes",
        "query_seconds",
        "startup_seconds",
        "total_seconds",
        "workspace_disk_bytes",
    }

    assert ceilings["schema_version"] == "bijux.canon.resource_ceilings.v1"
    assert set(ceilings["profiles"]) == {"local-cpu-hybrid", "offline-lexical"}
    assert all(
        set(profile) == required and all(value > 0 for value in profile.values())
        for profile in ceilings["profiles"].values()
    )
