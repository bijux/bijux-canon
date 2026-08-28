# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

from bijux_canon_index.infra.adapters.sqlite.lexical import (
    LexicalChunk,
    LexicalIndexCorruptionError,
    SQLiteLexicalIndex,
)


def _chunks() -> tuple[LexicalChunk, ...]:
    return (
        LexicalChunk(
            chunk_id="chunk-b",
            document_id="document-b",
            ordinal=0,
            text="Ancient DNA preserves evidence of population migration.",
            metadata={"language": "en", "year": 2024, "reviewed": True},
        ),
        LexicalChunk(
            chunk_id="chunk-a",
            document_id="document-a",
            ordinal=0,
            text="Ancient DNA extraction requires contamination controls.",
            metadata={"language": "en", "year": 2023, "reviewed": True},
        ),
        LexicalChunk(
            chunk_id="chunk-c",
            document_id="document-c",
            ordinal=0,
            text="Modern protein analysis uses mass spectrometry.",
            metadata={"language": "en", "year": 2024, "reviewed": False},
        ),
    )


def test_sqlite_fts5_persists_bm25_results_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "lexical.sqlite"
    with SQLiteLexicalIndex.build(path, _chunks()) as built:
        first = built.query("ancient dna")
        manifest = built.manifest

    with SQLiteLexicalIndex(path) as reopened:
        second = reopened.query("ancient dna")
        assert reopened.manifest == manifest

    assert first == second
    assert [result.chunk.chunk_id for result in first] == ["chunk-a", "chunk-b"]
    assert [result.rank for result in first] == [1, 2]
    assert all(result.score > 0 for result in first)
    with SQLiteLexicalIndex(path) as reopened:
        assert reopened.query("dna ancient") == first


def test_sqlite_fts5_applies_exact_metadata_and_document_filters(
    tmp_path: Path,
) -> None:
    with SQLiteLexicalIndex.build(tmp_path / "lexical.sqlite", _chunks()) as index:
        assert [
            result.chunk.chunk_id
            for result in index.query("ancient dna", filters={"year": 2024})
        ] == ["chunk-b"]
        assert [
            result.chunk.chunk_id
            for result in index.query(
                "ancient dna",
                filters={"reviewed": True, "language": "en"},
                document_ids=["document-a"],
            )
        ] == ["chunk-a"]
        assert index.query("ancient dna", document_ids=[]) == ()


def test_sqlite_fts5_build_identity_is_input_order_independent(tmp_path: Path) -> None:
    with SQLiteLexicalIndex.build(tmp_path / "forward.sqlite", _chunks()) as forward:
        forward_manifest = forward.manifest
    with SQLiteLexicalIndex.build(
        tmp_path / "reverse.sqlite", reversed(_chunks())
    ) as reverse:
        reverse_manifest = reverse.manifest

    assert reverse_manifest == forward_manifest


def test_sqlite_fts5_rejects_duplicate_chunks_and_existing_destination(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lexical.sqlite"
    duplicate = (_chunks()[0], _chunks()[0])
    with pytest.raises(ValueError, match="unique"):
        SQLiteLexicalIndex.build(path, duplicate)

    with SQLiteLexicalIndex.build(path, _chunks()):
        pass
    with pytest.raises(FileExistsError):
        SQLiteLexicalIndex.build(path, _chunks())


def test_sqlite_fts5_failed_replacement_preserves_active_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "lexical.sqlite"
    with SQLiteLexicalIndex.build(path, _chunks()) as index:
        generation_id = index.manifest.generation_id

    def reject_publication(
        _source: os.PathLike[str], _target: os.PathLike[str]
    ) -> None:
        raise OSError("injected atomic publication failure")

    monkeypatch.setattr(os, "replace", reject_publication)
    with pytest.raises(OSError, match="publication failure"):
        SQLiteLexicalIndex.build(path, _chunks()[:2], replace=True)

    with SQLiteLexicalIndex(path) as reopened:
        assert reopened.manifest.generation_id == generation_id


def test_sqlite_fts5_detects_chunk_and_filter_corruption(tmp_path: Path) -> None:
    path = tmp_path / "lexical.sqlite"
    with SQLiteLexicalIndex.build(path, _chunks()):
        pass
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE lexical_chunks SET text='tampered' WHERE chunk_id='chunk-a'"
        )

    with pytest.raises(LexicalIndexCorruptionError, match="content"):
        SQLiteLexicalIndex(path)


def test_sqlite_fts5_detects_inverted_index_corruption(tmp_path: Path) -> None:
    path = tmp_path / "lexical.sqlite"
    with SQLiteLexicalIndex.build(path, _chunks()):
        pass
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            DELETE FROM lexical_search_data
            WHERE id=(SELECT max(id) FROM lexical_search_data)
            """
        )

    with pytest.raises(LexicalIndexCorruptionError, match="integrity"):
        SQLiteLexicalIndex(path)


def test_sqlite_fts5_rejects_invalid_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one"):
        SQLiteLexicalIndex.build(tmp_path / "empty.sqlite", ())
    with pytest.raises(ValueError, match="finite"):
        LexicalChunk("chunk", "document", 0, "text", {"score": float("nan")})

    with SQLiteLexicalIndex.build(tmp_path / "lexical.sqlite", _chunks()) as index:
        with pytest.raises(ValueError, match="must not be empty"):
            index.query("  ")
        with pytest.raises(ValueError, match="top_k"):
            index.query("ancient", top_k=0)


def test_sqlite_fts5_escapes_query_syntax(tmp_path: Path) -> None:
    chunks = (LexicalChunk("chunk-a", "document", 0, 'Quoted "DNA" evidence.', {}),)
    with SQLiteLexicalIndex.build(tmp_path / "lexical.sqlite", chunks) as index:
        assert index.query('quoted "DNA"')[0].chunk.chunk_id == "chunk-a"


def test_sqlite_fts5_preserves_declared_phrases_and_rejects_bad_quotes(
    tmp_path: Path,
) -> None:
    chunks = (
        LexicalChunk("chunk-a", "document-a", 0, "Ancient DNA evidence.", {}),
        LexicalChunk("chunk-b", "document-b", 0, "DNA from ancient remains.", {}),
    )
    with SQLiteLexicalIndex.build(tmp_path / "lexical.sqlite", chunks) as index:
        assert {hit.chunk.chunk_id for hit in index.query("ancient dna")} == {
            "chunk-a",
            "chunk-b",
        }
        assert [hit.chunk.chunk_id for hit in index.query('"ancient DNA"')] == [
            "chunk-a"
        ]
        with pytest.raises(ValueError, match="unterminated phrase"):
            index.query('"ancient DNA')


def test_sqlite_fts5_admits_natural_language_queries(tmp_path: Path) -> None:
    with SQLiteLexicalIndex.build(tmp_path / "lexical.sqlite", _chunks()) as index:
        hits = index.query("What evidence do ancient genomes preserve?")

    assert hits[0].chunk.chunk_id == "chunk-b"
    assert "chunk-c" not in {hit.chunk.chunk_id for hit in hits}
