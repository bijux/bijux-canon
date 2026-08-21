# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bijux_canon_index.domain.embedding import (
    ArtifactDigest,
    EmbeddingModelLock,
    EmbeddingProfile,
)
from bijux_canon_index.infra.embeddings.local_model import LocalEmbeddingModel


class _Encoded(list[list[float]]):
    dtype = "float32"


class _Model:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def encode(self, texts: list[str], **options: object) -> _Encoded:
        self.calls.append({"texts": texts, **options})
        return _Encoded(
            [[1.0, 0.0] if text == "first" else [0.0, 1.0] for text in texts]
        )


def _lock(root: Path) -> EmbeddingModelLock:
    artifact = root / "model.bin"
    artifact.write_bytes(b"model")
    profile = EmbeddingProfile(
        "test-local",
        "local",
        "test-provider",
        "test/model",
        "1" * 40,
        2,
        "float32",
        "l2",
        "mean",
        "test/tokenizer",
        "1" * 40,
        "Apache-2.0",
        "cpu",
        "finite-float32-l2",
        "required",
        "qualification",
        ("model.bin",),
    )
    digest = ArtifactDigest("model.bin", hashlib.sha256(b"model").hexdigest(), 5)
    return EmbeddingModelLock(profile, (digest,), (("test-runtime", "1"),))


def test_local_embedding_preserves_order_and_bounds_batch(tmp_path: Path) -> None:
    model = _Model()
    adapter = LocalEmbeddingModel(
        tmp_path,
        _lock(tmp_path),
        batch_size=2,
        device="cpu",
        loader=lambda root, device: model,
    )

    result = adapter.embed(("first", "second"))

    assert result.vectors == ((1.0, 0.0), (0.0, 1.0))
    assert result.device == "cpu"
    assert result.inference_threads == 1
    assert model.calls == [
        {
            "texts": ["first", "second"],
            "batch_size": 2,
            "normalize_embeddings": True,
            "convert_to_numpy": True,
            "show_progress_bar": False,
        }
    ]


def test_local_embedding_rejects_implicit_device_and_empty_input(
    tmp_path: Path,
) -> None:
    lock = _lock(tmp_path)
    with pytest.raises(ValueError, match="explicit"):
        LocalEmbeddingModel(tmp_path, lock, device="auto", loader=lambda *_: _Model())
    adapter = LocalEmbeddingModel(tmp_path, lock, loader=lambda *_: _Model())
    with pytest.raises(ValueError, match="non-empty"):
        adapter.embed(())


@pytest.mark.parametrize("batch_size", [0, 1025])
def test_local_embedding_rejects_unbounded_batch_size(
    tmp_path: Path,
    batch_size: int,
) -> None:
    with pytest.raises(ValueError, match="1..1024"):
        LocalEmbeddingModel(
            tmp_path,
            _lock(tmp_path),
            batch_size=batch_size,
            loader=lambda *_: _Model(),
        )


def test_local_embedding_rejects_output_count_mismatch(tmp_path: Path) -> None:
    model = _Model()
    model.encode = lambda *_args, **_options: _Encoded([[1.0, 0.0]])  # type: ignore[method-assign]
    adapter = LocalEmbeddingModel(tmp_path, _lock(tmp_path), loader=lambda *_: model)

    with pytest.raises(ValueError, match="output count"):
        adapter.embed(("first", "second"))
