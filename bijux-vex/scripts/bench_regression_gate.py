# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.2)
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    artifacts_dir = Path("benchmarks/artifacts")
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
    current = run_benchmark(
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

    baseline_mean = baseline.get("summary", {}).get("mean_ms", 0.0) or 0.0
    current_mean = current.get("summary", {}).get("mean_ms", 0.0) or 0.0
    if baseline_mean <= 0:
        print("Baseline mean_ms missing or zero; skipping regression check.")
        return 0
    slowdown = (current_mean / baseline_mean) - 1.0
    if slowdown > args.threshold:
        print(
            f"Performance regression detected: {slowdown * 100:.2f}% slower "
            f"(threshold {args.threshold * 100:.2f}%)."
        )
        return 1 if args.fail else 0
    print("Performance regression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
