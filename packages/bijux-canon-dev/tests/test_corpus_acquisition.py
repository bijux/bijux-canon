"""Policy and immutability checks for real-corpus acquisition."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any

import pytest

from bijux_canon_dev.corpus.acquisition import (
    acquire_record,
    acquisition_core,
    jats_media,
    read_bounded,
    sha256,
    validate_existing_source,
    validate_jats,
    validate_redirect_url,
    validate_request_url,
    write_exclusive,
)

DOI = "10.1371/journal.pone.0021247"


def _record() -> dict[str, Any]:
    return {
        "source_id": "plos-pone-0021247",
        "record_identity_sha256": "a" * 64,
        "doi": DOI,
        "title": "Reviewed title",
        "authors": ["A. Author"],
        "journal": "PLOS ONE",
        "publication_year": 2011,
        "preferred_media": "jats",
        "license": {"expression": "CC BY 4.0", "url": "https://example.test/license"},
        "attribution": "A. Author (2011). Reviewed title.",
        "access_terms": "public HTTPS access without authentication",
        "redistribution_terms": "redistribution with attribution",
        "retrieval_policy": {
            "admitted_media": ["jats"],
            "approved_request_origins": ["https://journals.plos.org"],
            "approved_redirect_origins": ["https://storage.googleapis.com"],
            "approved_redirect_path_prefix": "/plos-corpus-prod/",
            "maximum_response_bytes": 2_048,
            "authentication_allowed": False,
            "redirect_requires_matching_doi_path": True,
        },
        "media": [
            {
                "media_type": "text/xml",
                "role": "jats_manuscript",
                "transport": {
                    "request_url": "https://journals.plos.org/plosone/article/file?id=x&type=manuscript",
                    "final_origin": "https://storage.googleapis.com",
                    "final_path": f"/plos-corpus-prod/{DOI}/1/article.xml",
                },
            }
        ],
    }


def _jats(doi: str = DOI) -> bytes:
    padding = "evidence text " * 100
    return (
        f'<article><front><article-meta><article-id pub-id-type="doi">{doi}</article-id>'
        f"<abstract><p>{padding}</p></abstract></article-meta></front></article>"
    ).encode()


def test_policy_accepts_only_reviewed_request_and_redirect_namespaces() -> None:
    record = _record()
    policy = record["retrieval_policy"]
    validate_request_url(record["media"][0]["transport"]["request_url"], policy)
    validate_redirect_url(
        f"https://storage.googleapis.com/plos-corpus-prod/{DOI}/1/article.xml",
        doi=DOI,
        policy=policy,
    )

    with pytest.raises(ValueError, match="request origin"):
        validate_request_url("https://example.test/article.xml", policy)
    with pytest.raises(ValueError, match="redirect origin"):
        validate_redirect_url(
            f"https://example.test/plos-corpus-prod/{DOI}/1/article.xml",
            doi=DOI,
            policy=policy,
        )
    with pytest.raises(ValueError, match="reviewed DOI"):
        validate_redirect_url(
            "https://storage.googleapis.com/plos-corpus-prod/10.0/wrong/1/article.xml",
            doi=DOI,
            policy=policy,
        )


def test_media_selection_rejects_unreviewed_or_ambiguous_media() -> None:
    record = _record()
    assert jats_media(record)["role"] == "jats_manuscript"

    record["retrieval_policy"]["admitted_media"] = ["jats", "pdf"]
    with pytest.raises(ValueError, match="only JATS"):
        jats_media(record)


def test_bounded_reader_checks_header_and_stream_boundaries() -> None:
    assert read_bounded(BytesIO(b"abc"), maximum_bytes=3, content_length="3") == b"abc"
    with pytest.raises(ValueError, match="Content-Length"):
        read_bounded(BytesIO(b"abc"), maximum_bytes=2, content_length="3")
    with pytest.raises(ValueError, match="response exceeds"):
        read_bounded(BytesIO(b"abc"), maximum_bytes=2, content_length=None)


def test_jats_validation_requires_article_root_and_reviewed_doi() -> None:
    validate_jats(_jats(), doi=DOI)
    with pytest.raises(ValueError, match="root"):
        validate_jats(_jats().replace(b"article>", b"book>"), doi=DOI)
    with pytest.raises(ValueError, match="reviewed DOI"):
        validate_jats(_jats("10.0/wrong"), doi=DOI)
    with pytest.raises(ValueError, match="well-formed XML"):
        validate_jats(b"<article>" + b"x" * 1_024, doi=DOI)


def test_exclusive_storage_is_idempotent_and_rejects_replacement(
    tmp_path: Path,
) -> None:
    target = tmp_path / "object.xml"
    write_exclusive(target, b"first")
    write_exclusive(target, b"first")
    assert target.read_bytes() == b"first"
    assert target.stat().st_mode & 0o222 == 0
    with pytest.raises(RuntimeError, match="refusing to replace"):
        write_exclusive(target, b"second")


def test_stable_source_rejects_a_second_content_identity(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / f"{'b' * 64}.xml").write_bytes(b"old")
    with pytest.raises(RuntimeError, match="different acquired bytes"):
        validate_existing_source(source_root, "c" * 64)


def test_offline_replay_revalidates_receipt_bytes(tmp_path: Path) -> None:
    record = _record()
    corpus_root = tmp_path / "corpus"
    receipt_root = tmp_path / "receipts"
    body = _jats()
    core = acquisition_core(record, body=body, corpus_root=corpus_root)
    receipt = {
        **core,
        "retrieved_at": "2026-08-21T00:00:00Z",
        "transport": {},
        "receipt_identity_sha256": sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        ),
    }
    write_exclusive(corpus_root / core["local_path"], body)
    write_exclusive(
        receipt_root / f"{record['source_id']}.json",
        json.dumps(receipt).encode(),
    )

    assert acquire_record(
        record,
        corpus_root=corpus_root,
        receipt_root=receipt_root,
        refresh=False,
    )["sha256"] == sha256(body)
    (corpus_root / core["local_path"]).chmod(0o644)
    (corpus_root / core["local_path"]).write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="do not match"):
        acquire_record(
            record,
            corpus_root=corpus_root,
            receipt_root=receipt_root,
            refresh=False,
        )
