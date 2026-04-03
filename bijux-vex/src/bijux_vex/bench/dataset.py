# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np

DEFAULT_DIMENSION = 32
DEFAULT_QUERY_COUNT = 256
DEFAULT_SEED = 1337


@dataclass(frozen=True)
class BenchmarkDataset:
    documents: list[str]
    vectors: np.ndarray
    queries: np.ndarray
    dimension: int
    seed: int


def _generate_documents(size: int, rng: np.random.Generator) -> list[str]:
    vocab = [
        "alpha",
        "bravo",
        "charlie",
        "delta",
        "echo",
        "foxtrot",
        "golf",
        "hotel",
        "india",
        "juliet",
        "kilo",
        "lima",
        "mike",
        "november",
        "oscar",
        "papa",
        "quebec",
        "romeo",
        "sierra",
        "tango",
        "uniform",
        "victor",
        "whiskey",
        "xray",
        "yankee",
        "zulu",
    ]
    docs: list[str] = []
    for idx in range(size):
        words = rng.choice(vocab, size=8, replace=True)
        docs.append(f"doc-{idx:06d} " + " ".join(words))
    return docs


def generate_dataset(
    *,
    size: int,
    dimension: int = DEFAULT_DIMENSION,
    query_count: int = DEFAULT_QUERY_COUNT,
    seed: int = DEFAULT_SEED,
) -> BenchmarkDataset:
    import numpy as np

    rng = np.random.default_rng(seed)
    documents = _generate_documents(size, rng)
    vectors = rng.normal(size=(size, dimension)).astype(np.float32)
    queries = rng.normal(size=(query_count, dimension)).astype(np.float32)
    return BenchmarkDataset(
        documents=documents,
        vectors=vectors,
        queries=queries,
        dimension=dimension,
        seed=seed,
    )


def save_dataset(dataset: BenchmarkDataset, folder: Path) -> None:
    import numpy as np

    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "size": len(dataset.documents),
        "dimension": dataset.dimension,
        "query_count": int(dataset.queries.shape[0]),
        "seed": dataset.seed,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    with (folder / "documents.jsonl").open("w", encoding="utf-8") as handle:
        for doc in dataset.documents:
            handle.write(json.dumps({"text": doc}) + "\n")
    np.save(folder / "vectors.npy", dataset.vectors)
    np.save(folder / "queries.npy", dataset.queries)


def load_dataset(folder: Path) -> BenchmarkDataset:
    import numpy as np

    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    documents: list[str] = []
    with (folder / "documents.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            documents.append(payload["text"])
    vectors = np.load(folder / "vectors.npy")
    queries = np.load(folder / "queries.npy")
    return BenchmarkDataset(
        documents=documents,
        vectors=vectors,
        queries=queries,
        dimension=int(meta["dimension"]),
        seed=int(meta["seed"]),
    )


def dataset_folder(base_dir: Path, size: int, dimension: int, seed: int) -> Path:
    return base_dir / f"size_{size}_dim_{dimension}_seed_{seed}"
