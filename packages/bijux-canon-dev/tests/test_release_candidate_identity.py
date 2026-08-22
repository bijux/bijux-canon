from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from bijux_canon_dev.release.python_support_matrix import WheelRecord
from bijux_canon_dev.release.release_candidate_identity import (
    CandidatePackage,
    ReleaseCandidateIdentityError,
    _artifact_path,
    _changelog_has_version,
    analyze_release_candidate,
    validate_release_tag,
)


VERSION = "0.4.0"


def _package(
    root: Path,
    name: str,
    *,
    fallback: str = VERSION,
    changelog: bool = True,
) -> CandidatePackage:
    return CandidatePackage(
        distribution_name=name,
        package_key=f"{name}-key",
        package_class="canonical",
        pyproject_path=root / name / "pyproject.toml",
        changelog_path=root / name / "CHANGELOG.md",
        fallback_version=fallback,
        changelog_has_version=changelog,
    )


def _wheel(root: Path, name: str, version: str = VERSION) -> WheelRecord:
    return WheelRecord(
        path=root / f"{name.replace('-', '_')}-{version}-py3-none-any.whl",
        distribution_name=name,
        version=version,
        requires_python=">=3.11,<4",
        import_names=(name.replace("-", "_"),),
        console_scripts=(),
        sha256="a" * 64,
        byte_length=100,
    )


def test_stable_normalized_release_tag_is_accepted() -> None:
    assert validate_release_tag("v0.4.0") == VERSION


@pytest.mark.parametrize("tag", ["0.4.0", "v0.4", "v0.4.0rc1", "v0.4.0+local"])
def test_nonrelease_tag_forms_are_rejected(tag: str) -> None:
    with pytest.raises(ReleaseCandidateIdentityError):
        validate_release_tag(tag)


def test_candidate_requires_matching_source_and_wheel_versions(
    tmp_path: Path,
) -> None:
    results = analyze_release_candidate(
        version=VERSION,
        packages=(_package(tmp_path, "example"),),
        wheels=(_wheel(tmp_path, "example"),),
    )
    assert results[0]["status"] == "passed"
    assert results[0]["wheel_version"] == VERSION
    assert results[0]["package_key"] == "example-key"

    with pytest.raises(ReleaseCandidateIdentityError, match="wheel-version"):
        analyze_release_candidate(
            version=VERSION,
            packages=(_package(tmp_path, "example"),),
            wheels=(_wheel(tmp_path, "example", "0.3.9"),),
        )


def test_candidate_requires_fallback_and_changelog_alignment(tmp_path: Path) -> None:
    with pytest.raises(
        ReleaseCandidateIdentityError,
        match="fallback-version.*missing-candidate-changelog",
    ):
        analyze_release_candidate(
            version=VERSION,
            packages=(
                _package(tmp_path, "example", fallback="0.3.9", changelog=False),
            ),
            wheels=(_wheel(tmp_path, "example"),),
        )


def test_changelog_match_requires_a_release_heading() -> None:
    assert _changelog_has_version("## [0.4.0] - 2026-08-22\n", VERSION)
    assert _changelog_has_version("## 0.4.0 - 2026-08-22\n", VERSION)
    assert not _changelog_has_version("Preparing version 0.4.0.\n", VERSION)


def test_candidate_outputs_must_remain_under_artifacts(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    (repository / "artifacts").mkdir(parents=True)
    assert _artifact_path(
        repository / "artifacts" / "release" / "identity.json",
        repository,
        label="output",
    ).is_relative_to(repository / "artifacts")
    with pytest.raises(ReleaseCandidateIdentityError, match="repository artifacts"):
        _artifact_path(repository / "identity.json", repository, label="output")


def test_installed_command_is_published_by_the_dev_package() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["scripts"]["bijux-canon-release-candidate"] == (
        "bijux_canon_dev.release.release_candidate_identity:main"
    )
