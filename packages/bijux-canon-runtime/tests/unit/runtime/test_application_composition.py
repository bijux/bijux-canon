# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for durable Runtime v2 production application composition."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

import duckdb
import pytest

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexService,
)
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
    DagOperation,
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeOutputPolicy,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
)
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.application_composition import (
    compose_runtime_application_services,
)
from bijux_canon_runtime.runtime.execution import application_composition
from bijux_canon_runtime.runtime.execution.durable_jobs import JobStatus
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)


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
    with duckdb.connect(str(layout.database_path), read_only=True) as authority:
        job_row = authority.execute(
            """
            SELECT request_artifact_id, result_artifact_id
            FROM runtime_jobs WHERE job_id = ?
            """,
            (submitted.job_id,),
        ).fetchone()
        assert job_row == (
            completed.request_artifact_id,
            completed.result_artifact_id,
        )
        assert authority.execute(
            """
            SELECT count(*) FROM artifact_payloads
            WHERE artifact_id IN (?, ?)
            """,
            job_row,
        ).fetchone() == (2,)
    with sqlite3.connect(
        f"{layout.job_store_path.as_uri()}?mode=ro",
        uri=True,
    ) as legacy_jobs:
        assert legacy_jobs.execute("SELECT count(*) FROM runtime_jobs").fetchone() == (
            0,
        )
    lock = load_model_lock(layout.model_lock_path)
    (layout.model_root / lock.artifacts[0].path).unlink()

    with compose_runtime_application_services(
        configuration=configuration,
        max_workers=2,
    ) as restarted:
        assert restarted.status(submitted.job_id).status is JobStatus.SUCCEEDED
        assert restarted.result(submitted.job_id) == result
        assert restarted.inspect(str(result["run_id"])) == inspection


def test_installed_offline_lexical_workflow_never_requires_or_loads_a_model(
    tmp_path: Path,
) -> None:
    source = tmp_path / "papers"
    source.mkdir()
    (source / "evidence.md").write_text(
        "# Ancient DNA\n\nAncient genomes preserve direct population evidence.\n",
        encoding="utf-8",
    )
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "lexical-workspace"}
    )
    initialized = initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()

    assert configuration.embedding_model_path is None
    assert not layout.model_lock_path.exists()

    budget = RuntimeRequestBudget(30.0, 10_000_000, max_provider_tokens=1000)
    output_policy = RuntimeOutputPolicy(True, True, True)

    def completed_result(service, snapshot):
        completed = service.wait(snapshot.job_id, timeout_seconds=10.0)
        assert completed.status is JobStatus.SUCCEEDED
        return service.result(snapshot.job_id)

    with compose_runtime_application_services(
        configuration=configuration,
        max_workers=2,
    ) as service:
        corpus = completed_result(
            service,
            service.corpus(
                RuntimeOperationRequest(
                    request_id=RequestID("offline-corpus"),
                    operation=RuntimeRequestOperation.CORPUS_PREPARE,
                    execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
                    budget=budget,
                    replay_mode=ReplayMode.STRICT,
                    scope="local",
                    source_directory=str(source),
                ),
                idempotency_key="offline-corpus",
            ),
        )
        corpus_id = ArtifactID(str(corpus["terminal_artifact_ids"][0]))
        with pytest.raises(
            ApplicationCapabilityError,
            match="requires a verified locked local embedding model",
        ):
            service.index(
                RuntimeOperationRequest(
                    request_id=RequestID("refused-dense-index"),
                    operation=RuntimeRequestOperation.INDEX_BUILD,
                    execution_profile=ExecutionProfile.LOCAL_HYBRID_EXACT,
                    budget=budget,
                    replay_mode=ReplayMode.STRICT,
                    scope="local",
                    corpus_id=corpus_id,
                ),
                idempotency_key="refused-dense-index",
            )
        with duckdb.connect(str(layout.database_path), read_only=True) as authority:
            assert authority.execute(
                "SELECT count(*) FROM runtime_jobs"
            ).fetchone() == (1,)
        indexed = completed_result(
            service,
            service.index(
                RuntimeOperationRequest(
                    request_id=RequestID("offline-index"),
                    operation=RuntimeRequestOperation.INDEX_BUILD,
                    execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
                    budget=budget,
                    replay_mode=ReplayMode.STRICT,
                    scope="local",
                    corpus_id=corpus_id,
                ),
                idempotency_key="offline-index",
            ),
        )
        index_id = ArtifactID(str(indexed["terminal_artifact_ids"][0]))
        index_report = service.inspect_index(index_id)
        assert index_report["backend"] == "sqlite-fts5"

        operation_results = []
        for operation in (
            RuntimeRequestOperation.RETRIEVE,
            RuntimeRequestOperation.ASK,
            RuntimeRequestOperation.RESEARCH,
        ):
            request = RuntimeOperationRequest(
                request_id=RequestID(f"offline-{operation.value}"),
                operation=operation,
                execution_profile=ExecutionProfile.OFFLINE_LEXICAL,
                budget=budget,
                replay_mode=ReplayMode.STRICT,
                scope="local",
                query="What evidence do ancient genomes preserve?",
                index_id=index_id,
                top_k=1,
                provider=(
                    None
                    if operation is RuntimeRequestOperation.RETRIEVE
                    else "credential-free"
                ),
                output_policy=(
                    None
                    if operation is RuntimeRequestOperation.RETRIEVE
                    else output_policy
                ),
            )
            submit = {
                RuntimeRequestOperation.RETRIEVE: service.retrieve,
                RuntimeRequestOperation.ASK: service.ask,
                RuntimeRequestOperation.RESEARCH: service.research,
            }[operation]
            result = completed_result(
                service,
                submit(request, idempotency_key=f"offline-{operation.value}"),
            )
            operation_results.append(result)

        for result in (indexed, *operation_results):
            inspection = service.inspect(str(result["run_id"]))
            assert all(
                step.operation
                not in {DagOperation.EMBED.value, DagOperation.DENSE_INDEX.value}
                for step in inspection.steps
            )

    assert initialized.model_lock_artifact_id
    assert not layout.model_root.exists()


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


def test_dense_dimension_mismatch_is_refused_before_job_queueing(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    configuration = _initialized_configuration(tmp_path / "workspace", model)
    layout = configuration.require_workspace_layout()
    lock = load_model_lock(layout.model_lock_path)
    source_index = IndexService(tmp_path / "source-index")
    inspection = source_index.build(
        (
            AdmittedIndexChunk(
                chunk_id="sha256:" + "c" * 64,
                document_id="sha256:" + "d" * 64,
                ordinal=0,
                text="Dimension mismatch evidence.",
                vector=(1.0, 0.0, 0.0),
                metadata={},
            ),
        ),
        snapshot_artifact_id="sha256:" + "a" * 64,
        model_lock_artifact_id=lock.lock_id,
        limits=IndexBuildLimits(
            max_chunks=1,
            max_text_bytes=1000,
            max_vector_bytes=1000,
            max_metadata_bytes=1000,
        ),
    )
    archive = source_index.export(inspection.generation_id)
    index_artifact = AddressedArtifact.from_bytes(
        archive.canonical_bytes,
        schema_id="index.composite.v1",
        media_type="application/vnd.bijux.index-generation+json",
        producer="bijux-canon-runtime:dense-index",
    )
    store = AuthoritativeArtifactPayloadStore(
        payload_store=AtomicFilesystemArtifactPayloadStore(layout.cas_root),
        database_path=layout.database_path,
    )
    store.put(index_artifact)

    with compose_runtime_application_services(configuration=configuration) as service:
        with pytest.raises(
            ApplicationCapabilityError,
            match="dense index dimension differs",
        ):
            service.retrieve(
                RuntimeOperationRequest(
                    request_id=RequestID("dimension-mismatch"),
                    operation=RuntimeRequestOperation.RETRIEVE,
                    execution_profile=ExecutionProfile.LOCAL_HYBRID_EXACT,
                    budget=RuntimeRequestBudget(30.0, 10_000_000),
                    replay_mode=ReplayMode.STRICT,
                    scope="local",
                    query="What is retained?",
                    index_id=index_artifact.descriptor.artifact_id,
                    top_k=1,
                ),
                idempotency_key="dimension-mismatch",
            )

    with duckdb.connect(str(layout.database_path), read_only=True) as authority:
        assert authority.execute("SELECT count(*) FROM runtime_jobs").fetchone() == (0,)


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
