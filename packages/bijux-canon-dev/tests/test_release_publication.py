from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.release.publication_guard import (
    artifact_versions,
    assert_artifacts_match_version,
    assert_publishable_version,
)
from bijux_canon_dev.release.version_resolver import resolve_version

REPO_ROOT = Path(__file__).resolve().parents[3]


def _workspace_metadata() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return cast(dict[str, Any], data["tool"]["bijux_canon"])


def _package_path(package_name: str) -> Path:
    workspace = _workspace_metadata()
    package_dirs = cast(dict[str, str], workspace["package_dirs"])
    return REPO_ROOT / package_dirs[package_name]


@pytest.mark.parametrize(
    ("version", "allow_prerelease", "allow_local_version", "should_raise"),
    [
        ("0.3.0", False, False, False),
        ("0.3.1.dev5", False, False, True),
        ("0.3.1.dev5", True, False, False),
        ("0.3.0+dirty", False, False, True),
        ("0.3.0+dirty", False, True, False),
    ],
)
def test_assert_publishable_version_enforces_release_policy(
    version: str,
    allow_prerelease: bool,
    allow_local_version: bool,
    should_raise: bool,
) -> None:
    if should_raise:
        with pytest.raises(ValueError, match="version|prerelease|local build marker"):
            assert_publishable_version(
                version,
                allow_prerelease=allow_prerelease,
                allow_local_version=allow_local_version,
            )
    else:
        assert_publishable_version(
            version,
            allow_prerelease=allow_prerelease,
            allow_local_version=allow_local_version,
        )


def test_artifact_versions_parse_wheel_and_sdist_names(tmp_path: Path) -> None:
    wheel = tmp_path / "bijux_canon_runtime-0.3.0-py3-none-any.whl"
    sdist = tmp_path / "bijux-canon-runtime-0.3.0.tar.gz"
    wheel.write_text("", encoding="utf-8")
    sdist.write_text("", encoding="utf-8")

    assert artifact_versions(tmp_path) == {
        sdist.name: "0.3.0",
        wheel.name: "0.3.0",
    }
    assert_artifacts_match_version(tmp_path, "0.3.0")


def test_assert_artifacts_match_version_rejects_mismatched_files(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "bijux-canon-runtime-0.3.1.dev1.tar.gz"
    sdist.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact versions do not match"):
        assert_artifacts_match_version(tmp_path, "0.3.0")


def test_public_release_packages_resolve_same_version_as_hatch() -> None:
    workspace = _workspace_metadata()
    failures: list[str] = []

    for package_name in sorted(workspace["public_release_packages"]):
        package_root = _package_path(package_name)
        pyproject_path = package_root / "pyproject.toml"
        project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]
        distribution_name = str(project["name"])

        hatch = subprocess.run(
            [sys.executable, "-m", "hatch", "version"],
            capture_output=True,
            check=False,
            cwd=package_root,
            text=True,
        )
        if hatch.returncode != 0:
            failures.append(
                f"{package_name}: hatch version failed: {hatch.stderr.strip()}"
            )
            continue

        resolved = resolve_version(pyproject_path, distribution_name)
        hatch_version = hatch.stdout.strip()
        if resolved != hatch_version:
            failures.append(
                f"{package_name}: resolver={resolved!r} hatch={hatch_version!r}"
            )

    assert not failures, "public package version resolution drifted:\n" + "\n".join(
        failures
    )
