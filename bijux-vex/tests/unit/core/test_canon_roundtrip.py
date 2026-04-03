# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import json

from bijux_vex.core.canon import canon
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import (
    Chunk,
    Document,
    ExecutionArtifact,
    ExecutionRequest,
    Result,
    Vector,
)


def _roundtrip(obj, builder):
    payload = json.loads(canon(obj).decode("utf-8"))
    rebuilt = builder(payload)
    assert fingerprint(obj) == fingerprint(rebuilt)


def test_roundtrip_core_objects():
    doc = Document(document_id="d1", text="hello", source="src", version="v1")
    chunk = Chunk(chunk_id="c1", document_id="d1", text="hello", ordinal=0)
    vec = Vector(
        vector_id="v1", chunk_id="c1", values=(0.1, 0.2), dimension=2, model="m1"
    )
    query = ExecutionRequest(
        request_id="q1",
        text=None,
        vector=(0.0, 0.0),
        top_k=5,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    result = Result(
        request_id="q1",
        document_id="d1",
        chunk_id="c1",
        vector_id="v1",
        artifact_id="i1",
        score=1.23,
        rank=1,
    )
    artifact = ExecutionArtifact(
        artifact_id="i1",
        corpus_fingerprint="corp",
        vector_fingerprint="vec",
        metric="l2",
        scoring_version="v1",
        build_params=(("a", "b"),),
        execution_contract=ExecutionContract.DETERMINISTIC,
    )

    _roundtrip(doc, lambda p: Document(**p))
    _roundtrip(chunk, lambda p: Chunk(**p))
    _roundtrip(vec, lambda p: Vector(**{**p, "values": tuple(p["values"])}))
    _roundtrip(
        query,
        lambda p: ExecutionRequest(
            request_id=p["request_id"],
            text=p.get("text"),
            vector=tuple(p["vector"]) if p.get("vector") is not None else None,
            top_k=p["top_k"],
            execution_contract=ExecutionContract(p["execution_contract"]),
            execution_intent=ExecutionIntent(p["execution_intent"]),
        ),
    )
    _roundtrip(result, lambda p: Result(**p))
    _roundtrip(
        artifact,
        lambda p: ExecutionArtifact(
            artifact_id=p["artifact_id"],
            corpus_fingerprint=p["corpus_fingerprint"],
            vector_fingerprint=p["vector_fingerprint"],
            metric=p["metric"],
            scoring_version=p["scoring_version"],
            schema_version=p.get("schema_version", "v1"),
            build_params=tuple(tuple(b) for b in p["build_params"]),
            artifact_fingerprint=p.get("artifact_fingerprint"),
            execution_contract=ExecutionContract(p["execution_contract"]),
        ),
    )


def test_dict_ordering_is_canonical():
    first = {"b": 1, "a": 2}
    second = {"a": 2, "b": 1}
    assert canon(first) == canon(second)


def test_list_ordering_changes_fingerprint():
    list_a = [1, 2, 3]
    list_b = [3, 2, 1]
    assert fingerprint(list_a) != fingerprint(list_b)
