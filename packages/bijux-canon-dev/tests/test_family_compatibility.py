from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from bijux_canon_dev.release.family_compatibility import (
    FamilyCompatibilityError,
    FamilyWheel,
    _artifact_path,
    _parser,
    analyze_family,
)


VERSION = "1.2.3"
PREVIOUS_VERSION = "1.2.2"


def _family(
    requirement: str = f"example-leaf=={VERSION}",
) -> tuple[FamilyWheel, FamilyWheel]:
    return (
        FamilyWheel("example-leaf", VERSION, ()),
        FamilyWheel("example-runtime", VERSION, (requirement,)),
    )


def test_exact_family_graph_proves_supported_and_rejected_combinations() -> None:
    edges, combinations = analyze_family(
        wheels=_family(),
        public_distributions=("example-leaf", "example-runtime"),
        publication_tiers=(("example-leaf",), ("example-runtime",)),
        expected_edges=(("example-runtime", "example-leaf"),),
        previous_version=PREVIOUS_VERSION,
    )

    assert [(edge.consumer, edge.provider) for edge in edges] == [
        ("example-runtime", "example-leaf")
    ]
    assert [item["supported"] for item in combinations] == [True, False, False]
    assert [item["combination_id"] for item in combinations] == [
        "example-runtime--example-leaf--current-current",
        "example-runtime--example-leaf--current-previous",
        "example-runtime--example-leaf--previous-current",
    ]


def test_broad_internal_dependency_is_rejected() -> None:
    with pytest.raises(
        FamilyCompatibilityError,
        match="internal dependency must use the candidate's exact version",
    ):
        analyze_family(
            wheels=_family("example-leaf>=1,<2"),
            public_distributions=("example-leaf", "example-runtime"),
            publication_tiers=(("example-leaf",), ("example-runtime",)),
            expected_edges=(("example-runtime", "example-leaf"),),
            previous_version=PREVIOUS_VERSION,
        )


def test_publication_tiers_must_follow_dependency_direction() -> None:
    with pytest.raises(
        FamilyCompatibilityError,
        match="publication order violates dependency direction",
    ):
        analyze_family(
            wheels=_family(),
            public_distributions=("example-leaf", "example-runtime"),
            publication_tiers=(("example-runtime",), ("example-leaf",)),
            expected_edges=(("example-runtime", "example-leaf"),),
            previous_version=PREVIOUS_VERSION,
        )


def test_run_products_must_remain_under_repository_artifacts(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    (repository / "artifacts").mkdir(parents=True)

    accepted = _artifact_path(
        repository / "artifacts" / "family" / "result.json",
        repository,
        label="output",
    )
    assert accepted == (repository / "artifacts" / "family" / "result.json").resolve()
    with pytest.raises(FamilyCompatibilityError, match="repository artifacts"):
        _artifact_path(
            repository / "family-compatibility.json",
            repository,
            label="output",
        )


def test_installed_command_is_published_by_the_dev_package() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["bijux-canon-family-compatibility"] == (
        "bijux_canon_dev.release.family_compatibility:main"
    )


def test_cli_requires_offline_dependency_wheelhouse() -> None:
    action = next(
        item for item in _parser()._actions if item.dest == "dependency_wheel_dir"
    )

    assert action.required is True
