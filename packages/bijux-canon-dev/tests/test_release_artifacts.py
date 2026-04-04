from __future__ import annotations

from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_LICENSE_SOURCE = "../../LICENSE"
GENERATED_VERSION_PACKAGES = {
    "bijux-canon-ingest": "src/bijux_canon_ingest/_build_version.py",
    "bijux-canon-reason": "src/bijux_canon_reason/_build_version.py",
    "bijux-canon-index": "src/bijux_canon_index/_build_version.py",
}


def _workspace_metadata() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["bijux_canon"]


def _package_path(package_name: str) -> Path:
    workspace = _workspace_metadata()
    return REPO_ROOT / workspace["package_dirs"][package_name]


def _pyproject_data(package_name: str) -> dict[str, object]:
    with (_package_path(package_name) / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_public_release_packages_ship_source_and_release_docs() -> None:
    workspace = _workspace_metadata()
    failures: list[str] = []

    for package_name in sorted(workspace["public_release_packages"]):
        data = _pyproject_data(package_name)
        wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
        sdist = data["tool"]["hatch"]["build"]["targets"]["sdist"]
        package_data = wheel.get("package-data", {})

        wheel_packages = wheel.get("packages", [])
        if not wheel_packages:
            failures.append(f"{package_name}: wheel build should declare source packages")
            continue

        source_package_dir = str(wheel_packages[0])
        required_release_files = {
            "README.md",
            "CHANGELOG.md",
            "docs/maintainer/pypi.md",
            f"{source_package_dir}/**",
        }

        sdist_include = set(sdist.get("include", []))

        missing_sdist = sorted(required_release_files - sdist_include)
        if missing_sdist:
            failures.append(f"{package_name}: sdist include missing {', '.join(missing_sdist)}")

        typed_marker = f"{source_package_dir}/py.typed"
        wheel_include = set(wheel.get("include", []))
        package_name_key = source_package_dir.rsplit("/", 1)[-1]
        wheel_package_data = set(package_data.get(package_name_key, []))
        if typed_marker not in wheel_include and "py.typed" not in wheel_package_data:
            failures.append(f"{package_name}: wheel include should keep {typed_marker}")

        if package_name.startswith("compat-"):
            compat_files = {"overview.md", "hatch_build.py"}
            missing_compat_sdist = sorted(compat_files - sdist_include)
            if missing_compat_sdist:
                failures.append(
                    f"{package_name}: compatibility sdist include missing "
                    + ", ".join(missing_compat_sdist)
                )

    assert not failures, "release artifact configuration failed:\n" + "\n".join(failures)


def test_public_release_packages_force_include_license_artifact() -> None:
    workspace = _workspace_metadata()
    failures: list[str] = []

    for package_name in sorted(workspace["public_release_packages"]):
        build = _pyproject_data(package_name)["tool"]["hatch"]["build"]
        force_include = build.get("force-include", {})
        if force_include.get(PUBLIC_LICENSE_SOURCE) != "LICENSE":
            failures.append(f"{package_name}: build.force-include should map {PUBLIC_LICENSE_SOURCE} -> LICENSE")

    assert not failures, "license artifact configuration failed:\n" + "\n".join(failures)


def test_compatibility_packages_publish_package_local_ignore_rules() -> None:
    workspace = _workspace_metadata()
    failures: list[str] = []

    for package_name in sorted(workspace["compat_packages"]):
        package_root = _package_path(package_name)
        pyproject = _pyproject_data(package_name)
        build = pyproject["tool"]["hatch"]["build"]
        sdist = build["targets"]["sdist"]
        gitignore_path = package_root / ".gitignore"

        if not gitignore_path.exists():
            failures.append(f"{package_name}: missing package-local .gitignore")
        if build.get("ignore-vcs") is not True:
            failures.append(f"{package_name}: build.ignore-vcs should be true")
        if "exclude" not in sdist or "**/.gitignore" not in sdist["exclude"]:
            failures.append(f"{package_name}: sdist exclude should mention **/.gitignore")
        if "only-include" not in sdist:
            failures.append(f"{package_name}: sdist should declare only-include")

    assert not failures, "compatibility package ignore policy failed:\n" + "\n".join(failures)


def test_generated_version_files_write_to_ignored_build_modules() -> None:
    failures: list[str] = []

    for package_name, generated_version_path in GENERATED_VERSION_PACKAGES.items():
        package_root = _package_path(package_name)
        pyproject = _pyproject_data(package_name)
        version_file = pyproject["tool"]["hatch"]["build"]["hooks"]["vcs"]["version-file"]
        if version_file != generated_version_path:
            failures.append(f"{package_name}: version-file should be {generated_version_path}")

        version_wrapper = package_root / generated_version_path.replace("_build_version.py", "_version.py")
        version_text = version_wrapper.read_text(encoding="utf-8")
        if "from ._build_version import" not in version_text:
            failures.append(f"{package_name}: _version.py should load _build_version first")

        gitignore_text = (package_root / ".gitignore").read_text(encoding="utf-8")
        if generated_version_path not in gitignore_text:
            failures.append(f"{package_name}: .gitignore should ignore {generated_version_path}")

    assert not failures, "generated version module configuration failed:\n" + "\n".join(failures)
