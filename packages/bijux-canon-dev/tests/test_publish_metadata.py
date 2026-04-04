from __future__ import annotations

from pathlib import Path
import sys
import tomllib


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages"
CHANGELOG_URL_PREFIX = "https://github.com/bijux/bijux-canon/blob/main/"
PUBLIC_RELEASE_VERSION = "0.3.0"


def _package_pyprojects() -> list[Path]:
    return sorted(PACKAGE_ROOT.glob("*/pyproject.toml"))


def _project_table(pyproject_path: Path) -> dict[str, object]:
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)["project"]


def _workspace_metadata() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["bijux_canon"]


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


def test_public_release_matrix_excludes_internal_dev_package() -> None:
    workspace = _workspace_metadata()
    public_packages = workspace["public_release_packages"]
    internal_packages = workspace["internal_support_packages"]

    assert len(public_packages) == 10
    assert "bijux-canon-dev" not in public_packages
    assert internal_packages == ["bijux-canon-dev"]


def test_public_release_packages_are_aligned_to_v0_3_0() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])
    package_dirs = workspace["package_dirs"]

    misaligned: list[str] = []
    for package_name in public_packages:
        pyproject_path = REPO_ROOT / package_dirs[package_name] / "pyproject.toml"
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        version_config = data.get("tool", {}).get("hatch", {}).get("version", {})
        fallback = version_config.get("fallback-version")
        if fallback != PUBLIC_RELEASE_VERSION:
            misaligned.append(f"{package_name}: fallback-version={fallback!r}")
    assert not misaligned, "public release version alignment failed:\n" + "\n".join(misaligned)
