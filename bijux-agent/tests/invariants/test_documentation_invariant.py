from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _hash_file(path: Path) -> str:
    buf = path.read_bytes()
    return hashlib.sha256(buf).hexdigest()


def _read_index_paths(doc_root: Path) -> set[str]:
    lines = (doc_root / "docs" / "index.md").read_text(encoding="utf-8").splitlines()
    parsed: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        entry = stripped[2:].strip()
        path = entry.split(maxsplit=1)[0]
        parsed.add(path)
    return parsed


def test_documentation_invariant() -> None:
    doc_root = Path(__file__).resolve().parents[2]
    checksum_file = doc_root / "docs" / "doc_checksums.json"
    expected = json.loads(checksum_file.read_text(encoding="utf-8"))
    index_paths = _read_index_paths(doc_root)

    for relative, hint in expected.items():
        doc_path = doc_root / relative
        assert doc_path.exists(), f"{relative} missing"
        current_hash = _hash_file(doc_path)
        assert current_hash == hint, (
            f"{relative} checksum drifted (expected {hint}, got {current_hash})"
        )
        assert relative in index_paths, f"{relative} is not referenced in docs/index.md"


def test_docs_have_checksum_and_index_entry() -> None:
    doc_root = Path(__file__).resolve().parents[2]
    checksum_file = doc_root / "docs" / "doc_checksums.json"
    expected = set(json.loads(checksum_file.read_text(encoding="utf-8")).keys())
    actual = {
        str(path.relative_to(doc_root)).replace("\\", "/")
        for path in (doc_root / "docs").rglob("*.md")
    }
    extra = actual - expected
    assert not extra, (
        f"Markdown files not tracked in doc_checksums.json: {sorted(extra)}"
    )


def test_root_markdown_whitelist() -> None:
    allowed = {
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
    }
    markdown_files = {Path(p).name for p in Path().glob("*.md")}
    unexpected = markdown_files - allowed
    assert not unexpected, f"Unexpected root markdown files: {sorted(unexpected)}"
