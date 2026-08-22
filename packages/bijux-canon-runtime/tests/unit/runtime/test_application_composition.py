# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for durable Runtime v2 production application composition."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_runtime.model.execution.request_plan import (
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.application_composition import (
    compose_runtime_application_services,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import JobStatus


def test_composed_corpus_job_survives_application_restart_without_model_load(
    tmp_path: Path,
) -> None:
    source = tmp_path / "papers"
    source.mkdir()
    (source / "evidence.md").write_text(
        "# Evidence\n\nAncient genomes preserve direct population evidence.\n",
        encoding="utf-8",
    )
    state = tmp_path / "runtime-state"
    request = RuntimeOperationRequest(
        request_id=RequestID("request-composed-corpus"),
        operation=RuntimeRequestOperation.CORPUS_PREPARE,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=RuntimeRequestBudget(30.0, 10_000_000),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        source_directory=str(source),
    )

    with compose_runtime_application_services(
        working_root=state,
        model_root=tmp_path / "model-is-not-needed-for-corpus",
        max_workers=2,
    ) as service:
        submitted = service.corpus(request, idempotency_key="corpus-once")
        completed = service.wait(submitted.job_id, timeout_seconds=10.0)
        result = service.result(submitted.job_id)
        inspection = service.inspect(str(result["run_id"]))
        corpus_id = ArtifactID(str(result["terminal_artifact_ids"][0]))
        corpus = service.inspect_corpus(corpus_id)

        assert completed.status is JobStatus.SUCCEEDED
        assert inspection.status.value == "completed"
        assert corpus["schema_version"] == (
            "bijux.canon.ingest.corpus_publication.v1"
        )
        assert corpus["byte_length"] > 0

    with compose_runtime_application_services(
        working_root=state,
        model_root=tmp_path / "model-is-still-not-needed",
        max_workers=2,
    ) as restarted:
        assert restarted.status(submitted.job_id).status is JobStatus.SUCCEEDED
        assert restarted.result(submitted.job_id) == result
        assert restarted.inspect(str(result["run_id"])) == inspection
