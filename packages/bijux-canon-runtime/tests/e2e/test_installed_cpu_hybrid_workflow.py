# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.real_local]

_REPOSITORY_ROOT = Path(__file__).parents[4]
_EXAMPLE = _REPOSITORY_ROOT / "examples" / "ancient-dna-research"


@pytest.mark.timeout(1200)
def test_installed_wheels_complete_cpu_hybrid_workflow(tmp_path: Path) -> None:
    runtime_value = os.environ.get("BIJUX_CANON_RUNTIME_INSTALLED_COMMAND")
    index_value = os.environ.get("BIJUX_CANON_INDEX_INSTALLED_COMMAND")
    model_value = os.environ.get("BIJUX_CANON_INSTALLED_MODEL_DIRECTORY")
    if runtime_value is None or index_value is None or model_value is None:
        pytest.skip(
            "set installed Runtime, Index, and materialized model environment paths"
        )
    runtime = Path(runtime_value).resolve()
    index = Path(index_value).resolve()
    model = Path(model_value).resolve()
    assert runtime.is_file()
    assert index.is_file()
    assert model.is_dir()

    copied_example = tmp_path / "ancient-dna-research"
    (copied_example / "corpus").mkdir(parents=True)
    (copied_example / "truth").mkdir()
    for name in ("cpu_hybrid_workflow.py", "offline_lexical_workflow.py"):
        shutil.copy2(_EXAMPLE / name, copied_example)
    shutil.copytree(
        _EXAMPLE / "corpus" / "sources", copied_example / "corpus" / "sources"
    )
    for name in ("evaluation-cases.jsonl", "qrels.jsonl"):
        shutil.copy2(_EXAMPLE / "truth" / name, copied_example / "truth")

    command = [
        sys.executable,
        str(copied_example / "cpu_hybrid_workflow.py"),
        "--runtime-command",
        str(runtime),
        "--index-command",
        str(index),
        "--model-directory",
        str(model),
        "--workspace",
        str(tmp_path / "runtime-workspace"),
        "--evidence-directory",
        str(tmp_path / "evidence"),
    ]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    sandbox = Path("/usr/bin/sandbox-exec")
    if sys.platform == "darwin" and sandbox.is_file():
        command = [
            str(sandbox),
            "-p",
            "(version 1)(allow default)(deny network*)",
            *command,
        ]
        environment["BIJUX_CANON_NETWORK_ISOLATION"] = "os-denied"

    completed = subprocess.run(  # noqa: S603 - explicit installed acceptance CLI
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        timeout=750,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["result"] == "passed"
    assert summary["model"]["profile_id"] == "local-minilm-384"
    assert summary["model"]["validation_result"] == "passed"
    assert summary["model"]["dimension"] == 384
    assert summary["corpus"]["document_count"] == 8
    assert summary["corpus"]["chunk_count"] == 493
    assert summary["corpus"]["rejection_count"] == 0
    assert summary["index"]["dimension"] == 384
    assert summary["index"]["integrity"] == "verified"
    assert {
        (item["stage"], item["backend"]) for item in summary["index"]["segments"]
    } == {
        ("lexical", "sqlite-fts5"),
        ("dense_exact", "faiss-flat-ip"),
        ("dense_hnsw", "faiss-hnsw"),
    }
    assert summary["searches"]["exact"]["channels"] == [
        "dense-exact",
        "lexical",
    ]
    assert summary["searches"]["ann"]["channels"] == ["dense-ann", "lexical"]
    assert summary["searches"]["exact"]["deterministic_repeat"] is True
    assert summary["searches"]["ann"]["deterministic_repeat"] is True
    assert summary["searches"]["exact"]["run_id"] == summary["run_id"]
    assert summary["searches"]["ann"]["run_id"] == summary["run_id"]
    assert (
        summary["searches"]["exact"]["attempt_id"]
        != summary["searches"]["ann"]["attempt_id"]
    )
    assert summary["evaluation"]["query_count"] == 12
    assert summary["evaluation"]["qrel_count"] == 29
    for metric_id, floor in summary["evaluation"]["quality_floors"].items():
        assert summary["evaluation"]["metrics"][metric_id] >= floor
    assert summary["rag"]["case_count"] == 12
    assert summary["rag"]["development_disposition_matches"] == 12
    assert summary["rag"]["citation_resolution_ratio"] == 1.0
    assert summary["rag"]["grounding_admission_support_ratio"] == 1.0
    assert (
        summary["rag"]["verified_direct_support_claims"]
        == summary["rag"]["claim_count"]
    )
    assert summary["rag"]["structurally_ungrounded_material_claims"] == 0
    assert summary["rag"]["unsupported_material_claims"] == 0
    assert summary["rag"]["system_output_may_define_truth"] is False
    assert summary["rag"]["semantic_equivalence_review_status"] == (
        "pending-independent-review"
    )
    assert len(summary["rag"]["observations"]) == 12
    assert (tmp_path / "evidence" / "rag-system-outputs.jsonl").is_file()
    research = summary["research"]
    assert research["question_id"] == "adna-multihop-contamination-strategy"
    assert research["initial_answer_retained"] is True
    assert research["distinct_evidence_needs"] >= 2
    assert research["distinct_searches"] >= 2
    assert research["classification_count"] > 0
    assert (
        sum(research["classification_relations"].values())
        == research["classification_count"]
    )
    assert research["revision_outcome"] == "revised"
    assert research["answer_changed"] is True
    assert research["final_admitted_claim_count"] > 0
    assert research["final_citation_count"] > 0
    assert research["tool_failure_count"] == 0
    assert research["terminal_outcome"] in {"complete", "incomplete_budget"}
    assert research["stop_reasons"]
    for dimension in (
        "artifact_bytes",
        "candidates",
        "documents",
        "elapsed_ms",
        "evidence_items",
        "iterations",
        "retrievals",
        "tokens",
        "tool_calls",
    ):
        assert (
            research["budget_usage"][dimension] <= research["budget_limits"][dimension]
        )
    agentic = summary["agentic"]
    assert agentic["readiness"] == "ready"
    assert agentic["operation_sequence"] == [
        "embed",
        "lexical-index",
        "dense-index",
        "retrieve",
        "reason",
        "agent",
        "verify",
        "persist",
        "publish",
    ]
    assert agentic["tool_decision_count"] >= 2
    assert agentic["tool_execution_count"] == agentic["tool_decision_count"]
    assert agentic["causal_event_count"] >= 6
    assert agentic["default_tool_policy"] == "deny"
    assert agentic["terminal_outcome"] in {"converged", "incomplete_budget"}
    assert agentic["replay_attempt_id"] != agentic["attempt_id"]
    assert agentic["comparison_equivalent"] is True
    assert agentic["cancellation"]["status"] == "cancelled"
    assert agentic["cancellation"]["error_type"] == "DurableJobCancelled"
    assert summary["workspace"]["restart_ready_profiles"] == [
        "local-hybrid-exact",
        "local-hybrid-ann",
    ]
    assert all(
        "/packages/" not in path
        for path in summary["installed_environment"]["sys_path"]
    )
    if sys.platform == "darwin":
        assert summary["network_isolation"] == "os-denied"
