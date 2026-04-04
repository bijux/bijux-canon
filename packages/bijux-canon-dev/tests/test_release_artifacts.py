from __future__ import annotations

from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[3]


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
        build_include = data["tool"]["hatch"]["build"].get("include", [])

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
        build_include_set = set(build_include)

        missing_sdist = sorted(required_release_files - sdist_include)
        if missing_sdist:
            failures.append(f"{package_name}: sdist include missing {', '.join(missing_sdist)}")

        missing_build = sorted(required_release_files - build_include_set)
        if missing_build:
            failures.append(f"{package_name}: build include missing {', '.join(missing_build)}")

        typed_marker = f"{source_package_dir}/py.typed"
        wheel_include = set(wheel.get("include", []))
        if typed_marker not in wheel_include:
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
