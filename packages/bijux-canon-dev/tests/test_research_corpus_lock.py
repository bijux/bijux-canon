"""Provenance, drift, and restart checks for the research-corpus lock."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_corpus_lock import (
    acquisition_receipt_identity,
    build_lock,
    lock_identity,
    validate_acquisition_receipt,
    validate_lock_document,
    write_lock,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"


def test_tracked_research_corpus_lock_resolves_all_exact_source_bytes() -> None:
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    validate_lock_document(document, research_root=RESEARCH_ROOT)
    assert document["source_count"] == 8
    assert document["total_bytes"] == 1_056_810
    assert all(
        source["offline_redistribution"]["permitted"] for source in document["sources"]
    )
    assert all(source["retrieved_at"].endswith("Z") for source in document["sources"])


def test_lock_write_is_byte_stable_across_restart(tmp_path: Path) -> None:
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    target = tmp_path / "corpus.lock.json"
    write_lock(target, document)
    first = target.read_bytes()
    write_lock(target, document)
    assert target.read_bytes() == first


def test_lock_identity_rejects_attribution_tampering() -> None:
    document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    tampered = deepcopy(document)
    tampered["sources"][0]["attribution"] = "changed"
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_lock_document(tampered)


def _synthetic_source(tmp_path: Path) -> tuple[Path, Path, Path]:
    corpus_root = tmp_path / "corpus"
    receipt_root = tmp_path / "receipts"
    source_id = "source-one"
    body = b"<article>reviewed source bytes</article>"
    source_path = corpus_root / "sources/source-one.xml"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(body)
    manifest_source = {
        "source_id": source_id,
        "source_record_identity_sha256": "a" * 64,
        "acquisition_receipt_identity_sha256": "",
        "doi": "10.1/example",
        "title": "Example",
        "authors": ["A. Author"],
        "journal": "Example Journal",
        "publication_year": 2026,
        "media_type": "application/xml",
        "byte_count": len(body),
        "sha256": sha256(body),
        "license": {"expression": "CC BY 4.0", "url": "https://example.test/license"},
        "attribution": "A. Author (2026). Example.",
        "transformations": [],
        "local_path": "sources/source-one.xml",
        "inspection": {"supplementary_links": []},
        "limitations": [],
    }
    receipt_core = {
        "schema_version": "bijux.canon.corpus_acquisition_receipt.v1",
        "source_id": source_id,
        "source_record_identity_sha256": "a" * 64,
        "state": "checksummed",
        "doi": "10.1/example",
        "title": "Example",
        "authors": ["A. Author"],
        "journal": "Example Journal",
        "publication_year": 2026,
        "media_type": "application/xml",
        "byte_count": len(body),
        "sha256": sha256(body),
        "license": manifest_source["license"],
        "attribution": manifest_source["attribution"],
        "access_terms": "public",
        "redistribution_terms": "redistribution with attribution",
        "transformations": [],
        "local_path": f"objects/{source_id}/{sha256(body)}.xml",
        "corpus_root": str(corpus_root),
        "limitations": [],
    }
    receipt = {
        **receipt_core,
        "retrieved_at": "2026-08-22T00:00:00Z",
        "transport": {
            "status": 200,
            "content_type": "application/xml",
            "request_url": "https://example.test/source.xml",
            "final_origin": "https://example.test",
            "final_path": "/source.xml",
        },
        "receipt_identity_sha256": sha256(canonical(receipt_core)),
    }
    manifest_source["acquisition_receipt_identity_sha256"] = receipt[
        "receipt_identity_sha256"
    ]
    receipt_root.mkdir()
    (receipt_root / f"{source_id}.json").write_text(json.dumps(receipt))
    manifest_core = [
        {
            "source_id": source_id,
            "source_record_identity_sha256": "a" * 64,
            "acquisition_receipt_identity_sha256": receipt["receipt_identity_sha256"],
            "sha256": sha256(body),
        }
    ]
    manifest = {
        "schema_version": "bijux.canon.full_text_jats_portfolio.v1",
        "state": "materialized",
        "source_count": 1,
        "portfolio_identity_sha256": sha256(canonical(manifest_core)),
        "sources": [manifest_source],
    }
    manifest_path = corpus_root / "corpus-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, corpus_root, receipt_root


def test_builder_binds_receipt_and_materialized_bytes(tmp_path: Path) -> None:
    manifest, corpus_root, receipts = _synthetic_source(tmp_path)
    document = build_lock(
        manifest_path=manifest,
        corpus_root=corpus_root,
        receipt_root=receipts,
    )
    assert document["source_count"] == 1
    assert document["lock_identity_sha256"] == lock_identity(document)


def test_acquisition_receipt_identity_rejects_tampering(tmp_path: Path) -> None:
    _manifest, _corpus_root, receipts = _synthetic_source(tmp_path)
    receipt = json.loads((receipts / "source-one.json").read_text())
    assert receipt["receipt_identity_sha256"] == acquisition_receipt_identity(receipt)
    receipt["attribution"] = "changed"
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_acquisition_receipt(receipt)
