from __future__ import annotations

from pathlib import Path


def _read_index_paths(doc_root: Path) -> set[str]:
    lines = (doc_root / "docs" / "index.md").read_text(encoding="utf-8").splitlines()
    parsed: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- docs/"):
            continue
        entry = stripped[2:].strip()
        path = entry.split(maxsplit=1)[0]
        parsed.add(path)
    return parsed


def test_documentation_invariant() -> None:
    doc_root = Path(__file__).resolve().parents[2]
    index_paths = _read_index_paths(doc_root)
    actual = {
        str(path.relative_to(doc_root)).replace("\\", "/")
        for path in (doc_root / "docs").rglob("*.md")
    }
    missing = actual - index_paths
    assert not missing, f"Documentation files missing from docs/index.md: {sorted(missing)}"


def test_docs_index_has_no_missing_files() -> None:
    doc_root = Path(__file__).resolve().parents[2]
    index_paths = _read_index_paths(doc_root)
    actual = {
        str(path.relative_to(doc_root)).replace("\\", "/")
        for path in (doc_root / "docs").rglob("*.md")
    }
    extra = index_paths - actual
    assert not extra, f"docs/index.md references missing files: {sorted(extra)}"


def test_root_package_docs_home_exists() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    docs_home = repo_root / "docs" / "packages" / "bijux-canon-agent" / "index.md"
    assert docs_home.exists(), "root package docs home must exist"


def test_root_markdown_whitelist() -> None:
    allowed = {
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "README.md",
        "SECURITY.md",
    }
    markdown_files = {Path(p).name for p in Path().glob("*.md")}
    unexpected = markdown_files - allowed
    assert not unexpected, f"Unexpected root markdown files: {sorted(unexpected)}"
