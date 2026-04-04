from __future__ import annotations

from pathlib import Path
import sys
import tomllib


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages"
CHANGELOG_URL_PREFIX = "https://github.com/bijux/bijux-canon/blob/main/"
PUBLIC_RELEASE_VERSION = "0.3.0"
REQUIRED_PUBLIC_URLS = {
    "Homepage",
    "Repository",
    "Documentation",
    "Issues",
    "Changelog",
    "Security",
}
COMPATIBILITY_PACKAGES = {
    "compat-agentic-flows": {
        "distribution": "agentic-flows",
        "canonical": "bijux-canon-runtime",
        "script": "agentic-flows",
    },
    "compat-bijux-agent": {
        "distribution": "bijux-agent",
        "canonical": "bijux-canon-agent",
        "script": "bijux-agent",
    },
    "compat-bijux-rag": {
        "distribution": "bijux-rag",
        "canonical": "bijux-canon-ingest",
        "script": "bijux-rag",
    },
    "compat-bijux-rar": {
        "distribution": "bijux-rar",
        "canonical": "bijux-canon-reason",
        "script": "bijux-rar",
    },
    "compat-bijux-vex": {
        "distribution": "bijux-vex",
        "canonical": "bijux-canon-index",
        "script": "bijux-vex",
    },
}


def _package_pyprojects() -> list[Path]:
    return sorted(PACKAGE_ROOT.glob("*/pyproject.toml"))


def _project_table(pyproject_path: Path) -> dict[str, object]:
    with pyproject_path.open("rb") as handle:
        return tomllib.load(handle)["project"]


def _workspace_metadata() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["bijux_canon"]


def _package_path(package_name: str) -> Path:
    workspace = _workspace_metadata()
    return REPO_ROOT / workspace["package_dirs"][package_name]


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


def test_public_release_packages_share_required_project_urls() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    missing: list[str] = []
    for package_name in sorted(public_packages):
        pyproject_path = _package_path(package_name) / "pyproject.toml"
        project = _project_table(pyproject_path)
        url_keys = set(project.get("urls", {}))
        missing_keys = sorted(REQUIRED_PUBLIC_URLS - url_keys)
        if missing_keys:
            missing.append(f"{package_name}: {', '.join(missing_keys)}")
    assert not missing, "public package URLs are incomplete:\n" + "\n".join(missing)


def test_public_release_package_readmes_link_changelog_and_entrypoint() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    missing: list[str] = []
    for package_name in sorted(public_packages):
        readme = (_package_path(package_name) / "README.md").read_text(encoding="utf-8")
        if "## Read this next" not in readme:
            missing.append(f"{package_name}: missing 'Read this next' section")
        if "CHANGELOG.md" not in readme:
            missing.append(f"{package_name}: missing changelog link")
        if "## Primary entrypoint" not in readme:
            missing.append(f"{package_name}: missing 'Primary entrypoint' section")
    assert not missing, "public package README contract failed:\n" + "\n".join(missing)


def test_compatibility_packages_preserve_legacy_publication_contract() -> None:
    failures: list[str] = []
    for package_name, expectation in COMPATIBILITY_PACKAGES.items():
        package_root = _package_path(package_name)
        pyproject_path = package_root / "pyproject.toml"
        project = _project_table(pyproject_path)
        tool = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["tool"]
        readme = (package_root / "README.md").read_text(encoding="utf-8")
        overview = (package_root / "overview.md").read_text(encoding="utf-8")
        build_hook = (package_root / "hatch_build.py").read_text(encoding="utf-8")

        distribution = expectation["distribution"]
        canonical = expectation["canonical"]
        script = expectation["script"]

        description = str(project.get("description", ""))
        if project.get("name") != distribution:
            failures.append(f"{package_name}: project.name should stay {distribution!r}")
        if f"published {distribution} distribution" not in description:
            failures.append(f"{package_name}: description should mention published {distribution}")
        if canonical not in description:
            failures.append(f"{package_name}: description should mention canonical {canonical}")
        if "continuation of the published" not in readme or f"`{distribution}`" not in readme:
            failures.append(f"{package_name}: README should state the PyPI continuation")
        if f"`{canonical}==<same version>`" not in readme:
            failures.append(f"{package_name}: README should document the same-version dependency")
        if f"console script: `{script}`" not in readme:
            failures.append(f"{package_name}: README should document the legacy console script")
        if f"installs `{canonical}` at the same version" not in overview:
            failures.append(f"{package_name}: overview should explain the same-version install")
        tag_pattern = tool["hatch"]["version"]["tag-pattern"]
        if tag_pattern != f"^{canonical}/v(?P<version>.*)$":
            failures.append(f"{package_name}: unexpected tag-pattern {tag_pattern!r}")
        hook_canonical = tool["hatch"]["metadata"]["hooks"]["custom"]["canonical-name"]
        if hook_canonical != canonical:
            failures.append(f"{package_name}: canonical-name should be {canonical!r}")
        if 'metadata["dependencies"] = [f"{canonical_name}=={version}"]' not in build_hook:
            failures.append(f"{package_name}: build hook must pin the canonical package to the same version")

    assert not failures, "compatibility publication contract failed:\n" + "\n".join(failures)
