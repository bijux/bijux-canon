# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from bijux_vex.bench.dataset import (
    DEFAULT_DIMENSION,
    DEFAULT_QUERY_COUNT,
    DEFAULT_SEED,
    dataset_folder,
    generate_dataset,
    load_dataset,
    save_dataset,
)
from bijux_vex.bench.runner import run_benchmark


def main() -> int:
    artifacts_dir = Path("benchmarks/artifacts")
    baseline_path = Path("benchmarks/baselines/v0.2.0.json")
    folder = dataset_folder(artifacts_dir, 1000, DEFAULT_DIMENSION, DEFAULT_SEED)
    if not folder.exists():
        dataset = generate_dataset(
            size=1000,
            dimension=DEFAULT_DIMENSION,
            query_count=DEFAULT_QUERY_COUNT,
            seed=DEFAULT_SEED,
        )
        save_dataset(dataset, folder)
    dataset = load_dataset(folder)
    result = run_benchmark(
        documents=dataset.documents,
        vectors=dataset.vectors,
        queries=dataset.queries,
        store_backend=None,
        store_uri=None,
        mode="exact",
        top_k=5,
        repeats=1,
        warmup=1,
    )
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
