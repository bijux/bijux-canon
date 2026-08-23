# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for durable Runtime v2 production application composition."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading

import pytest

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import (
    load_model_lock,
    materialize_model,
)
from bijux_canon_runtime.application.operations import ApplicationCapabilityError
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    initialize_runtime_workspace,
)
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
from bijux_canon_runtime.runtime.execution import application_composition
from bijux_canon_runtime.runtime.execution.durable_jobs import JobStatus


def _materialized_model(tmp_path: Path) -> Path:
    cache_root = tmp_path / "model-cache"
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    materialize_model(
        LOCAL_MINILM_PROFILE,
        cache_root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch,
    )
    return cache_root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision


def _initialized_configuration(
    workspace: Path,
    model: Path,
    **overrides: object,
) -> RuntimeConfiguration:
    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "working_root": workspace,
            **overrides,
        }
    )
    initialize_runtime_workspace(configuration)
    return configuration


def _corpus_request(source: Path, request_id: str) -> RuntimeOperationRequest:
    return RuntimeOperationRequest(
        request_id=RequestID(request_id),
        operation=RuntimeRequestOperation.CORPUS_PREPARE,
        execution_profile=ExecutionProfile.LOCAL_HYBRID_ANN,
        budget=RuntimeRequestBudget(30.0, 10_000_000),
        replay_mode=ReplayMode.STRICT,
        scope="local",
        source_directory=str(source),
    )


def test_composed_corpus_job_survives_application_restart_without_model_load(
    tmp_path: Path,
) -> None:
    source = tmp_path / "papers"
    source.mkdir()
    (source / "evidence.md").write_text(
        "# Evidence\n\nAncient genomes preserve direct population evidence.\n",
        encoding="utf-8",
    )
    configuration = _initialized_configuration(
        tmp_path / "runtime-state",
        _materialized_model(tmp_path),
    )
    request = _corpus_request(source, "request-composed-corpus")

    with compose_runtime_application_services(
        configuration=configuration,
        max_workers=2,
    ) as service:
        submitted = service.corpus(request, idempotency_key="corpus-once")
        completed = service.wait(submitted.job_id, timeout_seconds=10.0)
        result = service.result(submitted.job_id)
        inspection = service.inspect(str(result["run_id"]))
        terminal_artifact_ids = result["terminal_artifact_ids"]
        assert isinstance(terminal_artifact_ids, list)
        corpus_id = ArtifactID(str(terminal_artifact_ids[0]))
        corpus = service.inspect_corpus(corpus_id)

        assert completed.status is JobStatus.SUCCEEDED
        assert inspection.status.value == "completed"
        workspace_manifest = json.loads(
            configuration.require_workspace_layout().manifest_path.read_bytes()
        )
        assert inspection.attempts[0].process_id == (
            f"bijux-canon-runtime-v2:{workspace_manifest['workspace_id']}"
        )
        assert corpus["schema_version"] == ("bijux.canon.ingest.corpus_publication.v1")
        assert isinstance(corpus["byte_length"], int)
        assert corpus["byte_length"] > 0

    layout = configuration.require_workspace_layout()
    lock = load_model_lock(layout.model_lock_path)
    (layout.model_root / lock.artifacts[0].path).unlink()

    with compose_runtime_application_services(
        configuration=configuration,
        max_workers=2,
    ) as restarted:
        assert restarted.status(submitted.job_id).status is JobStatus.SUCCEEDED
        assert restarted.result(submitted.job_id) == result
        assert restarted.inspect(str(result["run_id"])) == inspection


def test_composition_refuses_an_uninitialized_effective_workspace(
    tmp_path: Path,
) -> None:
    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": tmp_path / "missing-model",
            "working_root": tmp_path / "missing-workspace",
        }
    )

    with pytest.raises(ApplicationCapabilityError, match="not_initialized"):
        compose_runtime_application_services(configuration=configuration)

    assert not (tmp_path / "missing-workspace").exists()


def test_two_composed_workspaces_cannot_cross_read_or_write(
    tmp_path: Path,
) -> None:
    source = tmp_path / "papers"
    source.mkdir()
    (source / "evidence.md").write_text(
        "# Evidence\n\nWorkspace isolation is observable.\n",
        encoding="utf-8",
    )
    model = _materialized_model(tmp_path)
    first_configuration = _initialized_configuration(
        tmp_path / "workspace-a",
        model,
    )
    second_configuration = _initialized_configuration(
        tmp_path / "workspace-b",
        model,
    )

    with (
        compose_runtime_application_services(
            configuration=first_configuration,
            max_workers=1,
        ) as first,
        compose_runtime_application_services(
            configuration=second_configuration,
            max_workers=1,
        ) as second,
    ):
        first_job = first.corpus(
            _corpus_request(source, "request-workspace-a"),
            idempotency_key="workspace-a",
        )
        second_job = second.corpus(
            _corpus_request(source, "request-workspace-b"),
            idempotency_key="workspace-b",
        )
        first.wait(first_job.job_id, timeout_seconds=10.0)
        second.wait(second_job.job_id, timeout_seconds=10.0)

        with pytest.raises(KeyError):
            first.status(second_job.job_id)
        with pytest.raises(KeyError):
            second.status(first_job.job_id)

    first_layout = first_configuration.require_workspace_layout()
    second_layout = second_configuration.require_workspace_layout()
    assert first_layout.cas_root != second_layout.cas_root
    assert first_layout.job_store_path != second_layout.job_store_path
    assert tuple(first_layout.cas_root.rglob("descriptor.json"))
    assert tuple(second_layout.cas_root.rglob("descriptor.json"))


def test_composition_uses_safe_explicit_database_and_index_overrides(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    configuration = _initialized_configuration(
        workspace,
        _materialized_model(tmp_path),
        database_path=workspace / "metadata" / "execution.duckdb",
        retrieval_index_path=workspace / "retrieval-index",
    )
    layout = configuration.require_workspace_layout()

    with compose_runtime_application_services(configuration=configuration):
        pass

    assert layout.database_path.is_file()
    assert (layout.index_root / "generations").is_dir()
    assert not (workspace / "runtime.duckdb").exists()
    assert not (workspace / "indexes").exists()


def test_lazy_embedding_model_reuses_and_invalidates_the_exact_lock_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_root = tmp_path / "model"
    model_root.mkdir()
    lock_path = model_root / "model.lock.json"
    lock_path.write_text("first", encoding="utf-8")
    constructed: list[str] = []
    inference_started = threading.Event()
    release_inference = threading.Event()
    overlapping_inference = threading.Event()
    active_inferences = 0

    class _Model:
        def __init__(self, _root: Path, lock: str) -> None:
            constructed.append(lock)
            self.model_lock_id = "sha256:" + hashlib.sha256(lock.encode()).hexdigest()

        def embed(self, texts: object) -> object:
            nonlocal active_inferences
            active_inferences += 1
            if active_inferences > 1:
                overlapping_inference.set()
            inference_started.set()
            assert release_inference.wait(timeout=2.0)
            active_inferences -= 1
            return texts

    def load_lock(path: Path) -> str:
        value = path.read_text(encoding="utf-8")
        if value == "invalid":
            raise ValueError("invalid model lock")
        return value

    monkeypatch.setattr(application_composition, "load_model_lock", load_lock)
    monkeypatch.setattr(application_composition, "LocalEmbeddingModel", _Model)
    embedding = application_composition._LazyLocalEmbeddingModel(model_root)

    first_id = embedding.model_lock_id
    cold_observation = embedding.cache_observation()
    assert cold_observation["status"] == "cold"
    with ThreadPoolExecutor(max_workers=8) as executor:
        warm_ids = tuple(
            executor.map(lambda _ordinal: embedding.model_lock_id, range(15))
        )
    first_ids = (first_id, *warm_ids)

    assert len(set(first_ids)) == 1
    assert constructed == ["first"]
    observation = embedding.cache_observation()
    assert observation["cache_identity"] == first_ids[0]
    assert observation["hit_count"] == 15
    assert observation["invalidation_count"] == 0
    assert isinstance(observation["last_load_ms"], float)
    assert observation["load_count"] == 1
    assert observation["schema_version"] == (
        "bijux.canon.index.model_resource_cache.v1"
    )
    assert observation["status"] == "warm"

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_embedding = executor.submit(embedding.embed, ("first",))
        assert inference_started.wait(timeout=2.0)
        second_embedding = executor.submit(embedding.embed, ("second",))
        assert not overlapping_inference.wait(timeout=0.05)
        release_inference.set()
        assert first_embedding.result(timeout=2.0) == ("first",)
        assert second_embedding.result(timeout=2.0) == ("second",)
    assert not overlapping_inference.is_set()

    lock_path.write_text("second", encoding="utf-8")
    second_id = embedding.model_lock_id
    assert second_id != first_ids[0]
    assert constructed == ["first", "second"]
    assert embedding.cache_observation()["invalidation_count"] == 1
    assert embedding.cache_observation()["load_count"] == 2
    assert embedding.cache_observation()["status"] == "invalidated"

    lock_path.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid model lock"):
        _ = embedding.model_lock_id
    assert embedding.cache_observation()["cache_identity"] == second_id
    assert embedding.cache_observation()["load_count"] == 2

    embedding.close()
    assert embedding.cache_observation()["status"] == "cold"
