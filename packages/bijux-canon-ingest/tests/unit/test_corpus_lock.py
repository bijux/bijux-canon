# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_ingest.application.corpus_lock import (
    CorpusLockError,
    load_verified_corpus_lock,
)
from bijux_canon_ingest.application.source_discovery import discover_sources
from bijux_canon_ingest.domain.source_discovery import (
    DiscoveredSource,
    DiscoveryPolicy,
    DiscoveryRoot,
)

REPOSITORY = Path(__file__).parents[4]
FORMATS_PORTFOLIO = REPOSITORY / "examples" / "document-formats"
RESEARCH_PORTFOLIO = REPOSITORY / "examples" / "ancient-dna-research"


def _discover(root: Path) -> tuple[DiscoveredSource, ...]:
    result = discover_sources(
        DiscoveryPolicy(roots=(DiscoveryRoot("locked-corpus", root),))
    )
    assert result.complete
    return result.sources


def _copy_formats_portfolio(tmp_path: Path) -> tuple[Path, Path]:
    portfolio = tmp_path / "document-formats"
    shutil.copytree(FORMATS_PORTFOLIO, portfolio)
    return portfolio, portfolio / "corpus"


def _rewrite_lock(path: Path, document: dict[str, object]) -> None:
    core = {
        key: value for key, value in document.items() if key != "lock_identity_sha256"
    }
    document["lock_identity_sha256"] = hashlib.sha256(
        json.dumps(
            core,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    path.chmod(0o644)
    path.write_text(
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )


def test_automatically_verifies_real_parser_portfolio() -> None:
    root = FORMATS_PORTFOLIO / "corpus"

    result = load_verified_corpus_lock(root, _discover(root))

    assert result is not None
    assert result.discovery == "automatic"
    assert result.schema_version == "bijux.canon.parser_source_lock.v1"
    assert len(result.sources) == 7
    jats = next(
        source
        for source in result.sources
        if source.filesystem_path.name == "parser-jats-real.xml"
    )
    assert [record.source for record in jats.records] == [
        "corpus_lock",
        "corpus_lock",
        "acquisition_receipt",
    ]


def test_automatically_verifies_real_research_portfolio() -> None:
    root = RESEARCH_PORTFOLIO / "corpus" / "sources"

    result = load_verified_corpus_lock(root, _discover(root))

    assert result is not None
    assert result.discovery == "automatic"
    assert result.schema_version == "bijux.canon.research_corpus_lock.v1"
    assert len(result.sources) == 8
    assert all(
        [record.source for record in source.records]
        == ["corpus_lock", "acquisition_receipt"]
        for source in result.sources
    )


def test_explicit_lock_remains_valid_after_portfolio_move(tmp_path: Path) -> None:
    portfolio, root = _copy_formats_portfolio(tmp_path)

    result = load_verified_corpus_lock(
        root,
        _discover(root),
        lock_path=portfolio / "corpus.lock.json",
    )

    assert result is not None
    assert result.discovery == "explicit"
    assert len(result.sources) == 7


def test_absent_lock_keeps_unlocked_directory_supported(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    root.mkdir()
    (root / "evidence.txt").write_text("unlocked evidence", encoding="utf-8")

    assert load_verified_corpus_lock(root, _discover(root)) is None


def test_rejects_ambiguous_automatic_locks(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    root.mkdir()
    (root / "corpus.lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "corpus.lock.json").write_text("{}", encoding="utf-8")

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, ())

    assert raised.value.code == "ambiguous_lock"


def test_rejects_stale_locked_source_bytes(tmp_path: Path) -> None:
    _, root = _copy_formats_portfolio(tmp_path)
    source = root / "parser-text-real.txt"
    source.chmod(0o644)
    source.write_bytes(source.read_bytes() + b"\nchanged after locking\n")

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, _discover(root))

    assert raised.value.code == "content_checksum_mismatch"


def test_rejects_missing_discovered_source() -> None:
    root = FORMATS_PORTFOLIO / "corpus"
    sources = _discover(root)

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, sources[:-1])

    assert raised.value.code == "missing_source"


def test_rejects_extra_discovered_source(tmp_path: Path) -> None:
    root = FORMATS_PORTFOLIO / "corpus"
    sources = _discover(root)
    extra_path = tmp_path / "extra.txt"
    extra_path.write_text("extra", encoding="utf-8")
    extra = replace(
        sources[-1],
        filesystem_path=extra_path,
        relative_path="extra.txt",
        location_id="sha256:" + "1" * 64,
        content_sha256=hashlib.sha256(b"extra").hexdigest(),
        byte_length=5,
    )

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, (*sources, extra))

    assert raised.value.code == "extra_source"


def test_rejects_tampered_lock_identity(tmp_path: Path) -> None:
    portfolio, root = _copy_formats_portfolio(tmp_path)
    lock_path = portfolio / "corpus.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["source_count"] = 6
    lock_path.chmod(0o644)
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, _discover(root))

    assert raised.value.code == "lock_identity_mismatch"


def test_rejects_malformed_lock(tmp_path: Path) -> None:
    portfolio, root = _copy_formats_portfolio(tmp_path)
    lock_path = portfolio / "corpus.lock.json"
    lock_path.chmod(0o644)
    lock_path.write_text("{", encoding="utf-8")

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, _discover(root))

    assert raised.value.code == "malformed_lock"


def test_rejects_tampered_acquisition_receipt(tmp_path: Path) -> None:
    portfolio, root = _copy_formats_portfolio(tmp_path)
    receipt_path = portfolio / "acquisition-receipts" / "parser-jats-real.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["attribution"] = "tampered attribution"
    receipt_path.chmod(0o644)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, _discover(root))

    assert raised.value.code == "acquisition_receipt_invalid"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("unsafe_path", "locked_path_invalid"),
        ("missing_license", "license_missing"),
        ("transport_mismatch", "acquisition_receipt_invalid"),
    ],
)
def test_rejects_semantically_invalid_rehashed_lock(
    tmp_path: Path, mutation: str, code: str
) -> None:
    portfolio, root = _copy_formats_portfolio(tmp_path)
    lock_path = portfolio / "corpus.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    source = lock["sources"][0]
    if mutation == "unsafe_path":
        source["local_path"] = "../escape.xml"
    elif mutation == "missing_license":
        source["license"] = {}
    else:
        source["transport_response_sha256"] = "0" * 64
    _rewrite_lock(lock_path, lock)

    with pytest.raises(CorpusLockError) as raised:
        load_verified_corpus_lock(root, _discover(root))

    assert raised.value.code == code
