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
    "Website",
    "Repository",
    "Documentation",
    "Issues",
    "Changelog",
    "Security",
}
BIJUX_SITE_URL = "https://bijux.io/"
BIJUX_CANON_DOCS_URL = "https://bijux.io/bijux-canon/"
PACKAGE_MAP_URL = "https://bijux.io/bijux-canon/package-map/"
COMPATIBILITY_GUIDE_URL = "https://bijux.io/bijux-canon/compat-packages/migration-guidance/"
LEGACY_NAME_MAP_URL = "https://bijux.io/bijux-canon/compat-packages/legacy-name-map/"
README_BADGE_MARKER = "https://img.shields.io"
EXPECTED_BADGE_COUNT = 19
EXPECTED_PYPI_GUIDE_BADGE_COUNT = 17
FORBIDDEN_STANDALONE_DOC_URLS = (
    "https://bijux.io/bijux-canon-runtime/",
    "https://bijux.io/bijux-canon-agent/",
    "https://bijux.io/bijux-canon-ingest/",
    "https://bijux.io/bijux-canon-reason/",
    "https://bijux.io/bijux-canon-index/",
    "https://bijux.io/bijux-canon-dev/",
)
COMPATIBILITY_PACKAGES = {
    "compat-agentic-flows": {
        "distribution": "agentic-flows",
        "canonical": "bijux-canon-runtime",
        "script": "agentic-flows",
        "retired_repo": "https://github.com/bijux/agentic-flows",
    },
    "compat-bijux-agent": {
        "distribution": "bijux-agent",
        "canonical": "bijux-canon-agent",
        "script": "bijux-agent",
        "retired_repo": "https://github.com/bijux/bijux-agent",
    },
    "compat-bijux-rag": {
        "distribution": "bijux-rag",
        "canonical": "bijux-canon-ingest",
        "script": "bijux-rag",
        "retired_repo": "https://github.com/bijux/bijux-rag",
    },
    "compat-bijux-rar": {
        "distribution": "bijux-rar",
        "canonical": "bijux-canon-reason",
        "script": "bijux-rar",
        "retired_repo": "https://github.com/bijux/bijux-rar",
    },
    "compat-bijux-vex": {
        "distribution": "bijux-vex",
        "canonical": "bijux-canon-index",
        "script": "bijux-vex",
        "retired_repo": "https://github.com/bijux/bijux-vex",
    },
}
CANONICAL_PACKAGES = {
    "bijux-canon-runtime": {
        "compatibility_package": "agentic-flows",
        "retired_repo": "https://github.com/bijux/agentic-flows",
    },
    "bijux-canon-agent": {
        "compatibility_package": "bijux-agent",
        "retired_repo": "https://github.com/bijux/bijux-agent",
    },
    "bijux-canon-ingest": {
        "compatibility_package": "bijux-rag",
        "retired_repo": "https://github.com/bijux/bijux-rag",
    },
    "bijux-canon-reason": {
        "compatibility_package": "bijux-rar",
        "retired_repo": "https://github.com/bijux/bijux-rar",
    },
    "bijux-canon-index": {
        "compatibility_package": "bijux-vex",
        "retired_repo": "https://github.com/bijux/bijux-vex",
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


def _shared_docs_url(package_name: str) -> str:
    return f"{BIJUX_CANON_DOCS_URL}{package_name}/"


def _compat_docs_url(distribution_name: str) -> str:
    return f"{BIJUX_CANON_DOCS_URL}compat-packages/{distribution_name}/"


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


def test_public_release_packages_prioritize_bijux_site_urls() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        project = _project_table(_package_path(package_name) / "pyproject.toml")
        urls = project.get("urls", {})
        for key in ("Homepage", "Website", "Documentation"):
            value = str(urls.get(key, ""))
            if not value.startswith(BIJUX_SITE_URL):
                failures.append(f"{package_name}: {key} should point to bijux.io")
    assert not failures, "public package URLs should prioritize bijux.io:\n" + "\n".join(failures)


def test_public_release_packages_use_shared_handbook_paths_for_docs() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        urls = _project_table(_package_path(package_name) / "pyproject.toml").get("urls", {})
        if package_name in CANONICAL_PACKAGES:
            expected_docs_url = _shared_docs_url(package_name)
        else:
            expected_docs_url = _compat_docs_url(COMPATIBILITY_PACKAGES[package_name]["distribution"])

        for key in ("Homepage", "Documentation"):
            if urls.get(key) != expected_docs_url:
                failures.append(f"{package_name}: {key} should point to {expected_docs_url}")

    assert not failures, "public package docs URLs failed:\n" + "\n".join(failures)


def test_public_release_packages_publish_family_navigation_urls() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        urls = _project_table(_package_path(package_name) / "pyproject.toml").get("urls", {})
        if package_name in CANONICAL_PACKAGES:
            if urls.get("PackageMap") != PACKAGE_MAP_URL:
                failures.append(f"{package_name}: PackageMap should point to the shared package map")
            if urls.get("CompatibilityGuide") != COMPATIBILITY_GUIDE_URL:
                failures.append(f"{package_name}: CompatibilityGuide should point to the shared migration guide")
        else:
            if urls.get("MigrationGuide") != COMPATIBILITY_GUIDE_URL:
                failures.append(f"{package_name}: MigrationGuide should point to the shared migration guide")
            if urls.get("LegacyNameMap") != LEGACY_NAME_MAP_URL:
                failures.append(f"{package_name}: LegacyNameMap should point to the shared legacy name map")
    assert not failures, "public package family navigation URLs failed:\n" + "\n".join(failures)


def test_public_release_packages_have_authors_maintainers_and_keywords() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        project = _project_table(_package_path(package_name) / "pyproject.toml")
        authors = project.get("authors", [])
        maintainers = project.get("maintainers", [])
        keywords = project.get("keywords", [])
        description = str(project.get("description", ""))

        if not authors:
            failures.append(f"{package_name}: missing authors")
        if not maintainers:
            failures.append(f"{package_name}: missing maintainers")
        if not description or "bijux" not in description.lower():
            failures.append(f"{package_name}: description should mention bijux")
        if len(keywords) < 4:
            failures.append(f"{package_name}: add more searchable keywords")
        if not any("bijux" in str(keyword).lower() for keyword in keywords):
            failures.append(f"{package_name}: keywords should include bijux")
        for group_name, group in (("authors", authors), ("maintainers", maintainers)):
            for entry in group:
                email = str(entry.get("email", ""))
                if not email.endswith("@bijux.io"):
                    failures.append(f"{package_name}: {group_name} should use @bijux.io emails")
    assert not failures, "public package people/keyword metadata failed:\n" + "\n".join(failures)


def test_public_release_package_readmes_link_changelog_and_entrypoint() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    missing: list[str] = []
    for package_name in sorted(public_packages):
        readme = (_package_path(package_name) / "README.md").read_text(encoding="utf-8")
        if "## Read this next" not in readme:
            missing.append(f"{package_name}: missing 'Read this next' section")
        if CHANGELOG_URL_PREFIX + f"packages/{package_name}/CHANGELOG.md" not in readme:
            missing.append(f"{package_name}: missing changelog URL")
        if "## Primary entrypoint" not in readme:
            missing.append(f"{package_name}: missing 'Primary entrypoint' section")
    assert not missing, "public package README contract failed:\n" + "\n".join(missing)


def test_public_release_package_readmes_publish_badges_and_absolute_links() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        readme = (_package_path(package_name) / "README.md").read_text(encoding="utf-8")
        if readme.count(README_BADGE_MARKER) < EXPECTED_BADGE_COUNT:
            failures.append(f"{package_name}: expected at least {EXPECTED_BADGE_COUNT} badges")
        if "https://pypi.org/project/bijux-canon-runtime/" not in readme:
            failures.append(f"{package_name}: README should advertise the canonical package family")
        if "https://bijux.io/bijux-canon/compat-packages/migration-guidance/" not in readme:
            failures.append(f"{package_name}: README should link the shared migration guide")
        if "](docs/" in readme or "](src/" in readme or "](tests)" in readme:
            failures.append(f"{package_name}: README should avoid PyPI-broken relative links")
    assert not failures, "public package README badge/link contract failed:\n" + "\n".join(failures)


def test_canonical_package_readmes_publish_legacy_continuity() -> None:
    failures: list[str] = []
    for package_name, expectation in CANONICAL_PACKAGES.items():
        readme = (_package_path(package_name) / "README.md").read_text(encoding="utf-8")
        compatibility_package = expectation["compatibility_package"]
        retired_repo = expectation["retired_repo"]

        if "## Legacy continuity" not in readme:
            failures.append(f"{package_name}: missing legacy continuity section")
        if f"https://pypi.org/project/{compatibility_package}/" not in readme:
            failures.append(f"{package_name}: missing compatibility package link")
        if retired_repo not in readme:
            failures.append(f"{package_name}: missing retired repository guidance")
    assert not failures, "canonical package legacy continuity failed:\n" + "\n".join(failures)


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
        retired_repo = expectation["retired_repo"]

        description = str(project.get("description", ""))
        if project.get("name") != distribution:
            failures.append(f"{package_name}: project.name should stay {distribution!r}")
        if f"{distribution} PyPI package" not in description:
            failures.append(f"{package_name}: description should mention the legacy PyPI package")
        if canonical not in description:
            failures.append(f"{package_name}: description should mention canonical {canonical}")
        if "Preserves installs, imports" not in description:
            failures.append(f"{package_name}: description should explain legacy compatibility")
        if "continuation of the published" not in readme or f"`{distribution}`" not in readme:
            failures.append(f"{package_name}: README should state the PyPI continuation")
        if "## Migration note" not in readme:
            failures.append(f"{package_name}: README should include a migration note")
        if f"`{canonical}==<same version>`" not in readme:
            failures.append(f"{package_name}: README should document the same-version dependency")
        if f"console script: `{script}`" not in readme:
            failures.append(f"{package_name}: README should document the legacy console script")
        legacy_handbook = _compat_docs_url(distribution)
        if legacy_handbook not in readme:
            failures.append(f"{package_name}: README should link the legacy package handbook")
        if legacy_handbook not in overview:
            failures.append(f"{package_name}: overview should link the legacy package handbook")
        if retired_repo not in readme:
            failures.append(f"{package_name}: README should document the retired repository")
        if f"installs `{canonical}` at the same version" not in overview:
            failures.append(f"{package_name}: overview should explain the same-version install")
        if retired_repo not in overview:
            failures.append(f"{package_name}: overview should document the retired repository")
        tag_pattern = tool["hatch"]["version"]["tag-pattern"]
        if tag_pattern != f"^{canonical}/v(?P<version>.*)$":
            failures.append(f"{package_name}: unexpected tag-pattern {tag_pattern!r}")
        hook_canonical = tool["hatch"]["metadata"]["hooks"]["custom"]["canonical-name"]
        if hook_canonical != canonical:
            failures.append(f"{package_name}: canonical-name should be {canonical!r}")
        if 'metadata["dependencies"] = [f"{canonical_name}=={version}"]' not in build_hook:
            failures.append(f"{package_name}: build hook must pin the canonical package to the same version")
        scripts = project.get("scripts", {})
        if script not in scripts:
            failures.append(f"{package_name}: legacy console script should be declared in project.scripts")

    assert not failures, "compatibility publication contract failed:\n" + "\n".join(failures)


def test_public_release_packages_ship_package_local_publication_guides() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        package_root = _package_path(package_name)
        guide_path = package_root / "docs" / "maintainer" / "pypi.md"
        if not guide_path.exists():
            failures.append(f"{package_name}: missing docs/maintainer/pypi.md")
            continue

        pyproject_text = (package_root / "pyproject.toml").read_text(encoding="utf-8")
        if "docs/maintainer/pypi.md" not in pyproject_text:
            failures.append(f"{package_name}: pyproject should ship docs/maintainer/pypi.md")

    assert not failures, "public package publication guides failed:\n" + "\n".join(failures)


def test_public_release_package_publication_guides_publish_family_badges() -> None:
    workspace = _workspace_metadata()
    public_packages = set(workspace["public_release_packages"])

    failures: list[str] = []
    for package_name in sorted(public_packages):
        guide = (_package_path(package_name) / "docs" / "maintainer" / "pypi.md").read_text(
            encoding="utf-8"
        )
        if guide.count(README_BADGE_MARKER) < EXPECTED_PYPI_GUIDE_BADGE_COUNT:
            failures.append(
                f"{package_name}: expected at least {EXPECTED_PYPI_GUIDE_BADGE_COUNT} badges in pypi.md"
            )
        if "https://pypi.org/project/bijux-canon-runtime/" not in guide:
            failures.append(f"{package_name}: pypi.md should advertise the canonical package family")
        if "https://pypi.org/project/bijux-vex/" not in guide:
            failures.append(f"{package_name}: pypi.md should advertise the compatibility package family")
        for ci_slug in ("runtime", "agent", "ingest", "reason", "index"):
            ci_url = f"https://github.com/bijux/bijux-canon/actions/workflows/ci-bijux-canon-{ci_slug}.yml"
            if ci_url not in guide:
                failures.append(f"{package_name}: pypi.md should advertise {ci_slug} CI coverage")
        if _shared_docs_url("bijux-canon-runtime") not in guide:
            failures.append(f"{package_name}: pypi.md should link shared handbook package docs")

    assert not failures, "public package publication guide badges failed:\n" + "\n".join(failures)


def test_repository_docs_links_avoid_standalone_package_sites() -> None:
    failures: list[str] = []
    excluded_roots = {".git", ".tox", ".venv", "__pycache__", "artifacts", "node_modules"}

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".toml"}:
            continue
        if any(part in excluded_roots for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden_url in FORBIDDEN_STANDALONE_DOC_URLS:
            if forbidden_url in text:
                failures.append(f"{path.relative_to(REPO_ROOT)}: contains {forbidden_url}")

    assert not failures, "repository docs URLs failed:\n" + "\n".join(failures)
