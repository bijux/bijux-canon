#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    Vector,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.services.policies.id_policy import ContentAddressedIdPolicy


def _seed_backend(
    execution_contract: ExecutionContract,
) -> tuple[object, ExecutionArtifact]:
    backend = memory_backend()
    policy = ContentAddressedIdPolicy()
    documents = ["alpha", "beta", "gamma"]
    vectors = [(0.0, 1.0), (1.0, 0.0), (0.5, 0.5)]
    with backend.tx_factory() as tx:
        for idx, text in enumerate(documents):
            doc_id = policy.document_id(text)
            backend.stores.vectors.put_document(
                tx, Document(document_id=doc_id, text=text)
            )
            chunk_id = policy.chunk_id(doc_id, 0)
            backend.stores.vectors.put_chunk(
                tx,
                Chunk(chunk_id=chunk_id, document_id=doc_id, text=text, ordinal=0),
            )
            vec_id = policy.vector_id(chunk_id, vectors[idx])
            backend.stores.vectors.put_vector(
                tx,
                Vector(
                    vector_id=vec_id,
                    chunk_id=chunk_id,
                    values=vectors[idx],
                    dimension=len(vectors[idx]),
                ),
            )
        artifact = ExecutionArtifact(
            artifact_id="art-1",
            corpus_fingerprint="corp",
            vector_fingerprint="vec",
            metric="l2",
            scoring_version="v1",
            execution_contract=execution_contract,
        )
        backend.stores.ledger.put_artifact(tx, artifact)
    return backend, artifact


def _capture_cost(result) -> dict[str, object]:
    cost = result.cost
    return {
        "vector_reads": cost.vector_reads,
        "distance_computations": cost.distance_computations,
        "graph_hops": cost.graph_hops,
        "wall_time_estimate_ms": cost.wall_time_estimate_ms,
        "cpu_time_ms": cost.cpu_time_ms,
        "memory_estimate_mb": cost.memory_estimate_mb,
        "vector_ops": cost.vector_ops,
    }


def run_exact() -> dict[str, object]:
    backend, artifact = _seed_backend(ExecutionContract.DETERMINISTIC)
    request = ExecutionRequest(
        request_id="perf-exact",
        text=None,
        vector=(0.0, 1.0),
        top_k=2,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        execution_mode=ExecutionMode.STRICT,
    )
    session = start_execution_session(
        artifact,
        request,
        backend.stores,
        ann_runner=backend.ann,
    )
    result, _ = execute_request(session, backend.stores, ann_runner=backend.ann)
    return _capture_cost(result)


def run_ann() -> dict[str, object]:
    backend, artifact = _seed_backend(ExecutionContract.NON_DETERMINISTIC)
    request = ExecutionRequest(
        request_id="perf-ann",
        text=None,
        vector=(0.0, 1.0),
        top_k=2,
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=ExecutionBudget(
            max_latency_ms=10,
            max_memory_mb=10,
            max_error=0.5,
        ),
    )
    randomness = RandomnessProfile(
        seed=0,
        sources=("reference_ann_hnsw",),
        bounded=True,
        budget={"max_latency_ms": 10, "max_memory_mb": 10, "max_error": 0.5},
        envelopes=(
            ("max_latency_ms", 10.0),
            ("max_memory_mb", 10.0),
            ("max_error", 0.5),
        ),
    )
    session = start_execution_session(
        artifact,
        request,
        backend.stores,
        randomness=randomness,
        ann_runner=backend.ann,
    )
    result, _ = execute_request(session, backend.stores, ann_runner=backend.ann)
    return _capture_cost(result)


def main() -> int:
    output = {
        "memory_exact": run_exact(),
        "memory_ann": run_ann(),
    }
    out_path = Path("benchmarks/performance_baseline.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
