from __future__ import annotations

from pathlib import Path
import sys
import tomllib


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages"
CHANGELOG_URL_PREFIX = "https://github.com/bijux/bijux-canon/blob/main/"


def _package_pyprojects() -> list[Path]:
    return sorted(PACKAGE_ROOT.glob("*/pyproject.toml"))


def _project_table(pyproject_path: Path) -> dict[str, object]:
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)["project"]


def test_all_packages_have_package_local_changelogs() -> None:
    missing = [
        pyproject_path.parent.name
        for pyproject_path in _package_pyprojects()
        if not (pyproject_path.parent / "CHANGELOG.md").exists()
    ]
    assert not missing, f"missing package changelog files: {', '.join(missing)}"


def test_project_changelog_urls_point_to_checked_in_files() -> None:
    broken: list[str] = []
    for pyproject_path in _package_pyprojects():
        project = _project_table(pyproject_path)
        changelog_url = str(project.get("urls", {}).get("Changelog", ""))
        if not changelog_url.startswith(CHANGELOG_URL_PREFIX):
            broken.append(f"{pyproject_path.parent.name}: missing or invalid Changelog URL")
            continue
        relative_path = changelog_url.removeprefix(CHANGELOG_URL_PREFIX)
        if not (REPO_ROOT / relative_path).exists():
            broken.append(f"{pyproject_path.parent.name}: {relative_path}")
    assert not broken, "broken changelog metadata:\n" + "\n".join(broken)


def test_typed_packages_ship_py_typed_markers() -> None:
    missing: list[str] = []
    for pyproject_path in _package_pyprojects():
        project = _project_table(pyproject_path)
        classifiers = set(project.get("classifiers", []))
        if "Typing :: Typed" not in classifiers:
            continue
        if not list((pyproject_path.parent / "src").glob("*/py.typed")):
            missing.append(pyproject_path.parent.name)
    assert not missing, f"typed packages missing py.typed markers: {', '.join(missing)}"
