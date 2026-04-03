# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from bijux_vex.boundaries.api.app import app


def main() -> None:
    try:
        import faiss  # noqa: F401
    except Exception:
        print("faiss not installed; skipping demo_app")
        return

    with tempfile.TemporaryDirectory() as workdir:
        workdir_path = Path(workdir)
        os.environ["BIJUX_VEX_STATE_PATH"] = str(workdir_path / "session.sqlite")
        os.environ["BIJUX_VEX_RUN_DIR"] = str(workdir_path / "runs")
        os.environ["BIJUX_VEX_BACKEND"] = "sqlite"
        index_path = str(workdir_path / "demo.faiss")

        client = TestClient(app)

        client.post("/create", json={"name": "demo"})
        ingest = client.post(
            "/ingest",
            json={
                "documents": ["hello world", "hello bijux"],
                "vectors": [[0.0, 1.0, 0.0], [0.0, 0.9, 0.1]],
                "vector_store": "faiss",
                "vector_store_uri": index_path,
            },
        )
        ingest.raise_for_status()

        artifact = client.post(
            "/artifact",
            json={
                "execution_contract": "deterministic",
                "vector_store": "faiss",
                "vector_store_uri": index_path,
            },
        )
        artifact.raise_for_status()

        os.environ["BIJUX_VEX_ARTIFACT_ID"] = "art-2"
        nd_artifact = client.post(
            "/artifact",
            json={
                "execution_contract": "non_deterministic",
                "index_mode": "ann",
                "vector_store": "faiss",
                "vector_store_uri": index_path,
            },
        )
        nd_artifact.raise_for_status()

        deterministic = client.post(
            "/execute",
            json={
                "artifact_id": "art-1",
                "vector": [0.0, 1.0, 0.0],
                "top_k": 2,
                "execution_contract": "deterministic",
                "execution_intent": "exact_validation",
                "execution_mode": "strict",
                "vector_store": "faiss",
                "vector_store_uri": index_path,
            },
        )
        deterministic.raise_for_status()
        det_payload = deterministic.json()

        nondeterministic = client.post(
            "/execute",
            json={
                "artifact_id": "art-2",
                "vector": [0.0, 1.0, 0.0],
                "top_k": 2,
                "execution_contract": "non_deterministic",
                "execution_intent": "exploratory_search",
                "execution_mode": "bounded",
                "execution_budget": {"max_latency_ms": 2000},
                "randomness_profile": {
                    "seed": 42,
                    "sources": ["ann_probe"],
                    "bounded": True,
                },
                "nd_build_on_demand": True,
                "vector_store": "faiss",
                "vector_store_uri": index_path,
            },
        )
        nondeterministic.raise_for_status()
        nd_payload = nondeterministic.json()

        explain = client.post(
            "/explain",
            json={"result_id": det_payload["results"][0], "artifact_id": "art-1"},
        )
        explain.raise_for_status()

        det_set = set(det_payload["results"])
        nd_set = set(nd_payload["results"])
        overlap = det_set & nd_set

        report = {
            "deterministic": det_payload,
            "non_deterministic": nd_payload,
            "explain": explain.json(),
            "compare": {
                "overlap_ratio": len(overlap) / len(det_set or {1}),
                "deterministic_only": sorted(det_set - nd_set),
                "nondeterministic_only": sorted(nd_set - det_set),
            },
        }
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
