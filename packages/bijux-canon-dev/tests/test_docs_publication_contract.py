from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
BIJUX_CANON_DOCS_URL = "https://bijux.io/bijux-canon/"


def _workspace_metadata() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return cast(dict[str, Any], data["tool"]["bijux_canon"])


def _package_path(package_name: str) -> Path:
    workspace = _workspace_metadata()
    package_dirs = cast(dict[str, str], workspace["package_dirs"])
    return REPO_ROOT / package_dirs[package_name]


def _package_project(package_name: str) -> dict[str, Any]:
    with (_package_path(package_name) / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return cast(dict[str, Any], data["project"])


def _public_package_docs_urls() -> dict[str, str]:
    workspace = _workspace_metadata()
    urls: dict[str, str] = {}
    for package_name in workspace["public_release_packages"]:
        project_urls = _package_project(package_name).get("urls", {})
        urls[package_name] = str(project_urls["Documentation"])
    return urls


def _docs_source_path(docs_url: str) -> Path:
    assert docs_url.startswith(BIJUX_CANON_DOCS_URL), docs_url
    relative_path = docs_url.removeprefix(BIJUX_CANON_DOCS_URL).rstrip("/")
    docs_root = REPO_ROOT / "docs"
    candidates = [
        docs_root / relative_path / "index.md",
        docs_root / f"{relative_path}.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def test_public_package_documentation_urls_resolve_to_checked_in_pages() -> None:
    failures: list[str] = []
    for package_name, docs_url in sorted(_public_package_docs_urls().items()):
        docs_path = _docs_source_path(docs_url)
        if not docs_path.exists():
            failures.append(f"{package_name}: missing docs page for {docs_url}")
    assert not failures, "public package docs URLs failed:\n" + "\n".join(failures)


def test_root_readme_package_map_advertises_resolvable_docs_pages() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    failures: list[str] = []
    for package_name, docs_url in sorted(_public_package_docs_urls().items()):
        if docs_url not in readme:
            failures.append(f"{package_name}: README should advertise {docs_url}")
            continue
        docs_path = _docs_source_path(docs_url)
        if not docs_path.exists():
            failures.append(
                f"{package_name}: README points at missing docs page {docs_url}"
            )

    assert not failures, "README docs publication contract failed:\n" + "\n".join(
        failures
    )
