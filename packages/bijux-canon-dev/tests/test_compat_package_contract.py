from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPATIBILITY_TARGETS = {
    "compat-agentic-flows": {
        "canonical_import": "bijux_canon_runtime",
        "test_files": ["tests/unit/test_agentic_flows_compatibility_bridge.py"],
    },
    "compat-bijux-agent": {
        "canonical_import": "bijux_canon_agent",
        "test_files": ["tests/unit/test_bijux_agent_compatibility_bridge.py"],
    },
    "compat-bijux-rag": {
        "canonical_import": "bijux_canon_ingest",
        "test_files": ["tests/unit/test_bijux_rag_compatibility_bridge.py"],
    },
    "compat-bijux-rar": {
        "canonical_import": "bijux_canon_reason",
        "test_files": ["tests/unit/test_bijux_rar_compatibility_bridge.py"],
    },
    "compat-bijux-vex": {
        "canonical_import": "bijux_canon_index",
        "test_files": ["tests/unit/test_bijux_vex_compatibility_bridge.py"],
    },
}


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _as_str_list(value: object) -> list[str]:
    return cast(list[str], value)


def _workspace_metadata() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = cast(dict[str, object], tomllib.load(handle))
    tool = _as_dict(pyproject["tool"])
    return _as_dict(tool["bijux_canon"])


def test_compatibility_packages_are_explicitly_tracked_in_workspace_metadata() -> None:
    workspace = _workspace_metadata()

    assert set(_as_str_list(workspace["compat_packages"])) == set(COMPATIBILITY_TARGETS)


def test_compatibility_packages_keep_standardized_bridge_tests_while_they_stay_thin() -> (
    None
):
    failures: list[str] = []

    for package_name, metadata in COMPATIBILITY_TARGETS.items():
        contract = _as_dict(metadata)
        canonical_import = cast(str, contract["canonical_import"])
        expected_test_files = cast(list[str], contract["test_files"])
        package_root = REPO_ROOT / "packages" / package_name
        tests_dir = package_root / "tests"
        if not tests_dir.is_dir():
            failures.append(f"{package_name}: missing standardized compatibility tests")
        else:
            test_files = sorted(
                path.relative_to(package_root).as_posix()
                for path in tests_dir.rglob("test_*.py")
            )
            if test_files != expected_test_files:
                failures.append(
                    f"{package_name}: expected only {expected_test_files}, found {test_files}"
                )

        python_files = sorted(
            path.relative_to(package_root).as_posix()
            for path in package_root.glob("src/**/*.py")
        )
        if len(python_files) != 1:
            failures.append(
                f"{package_name}: expected exactly one compatibility module, found {python_files}"
            )
            continue

        module_path = package_root / python_files[0]
        module_text = module_path.read_text(encoding="utf-8")
        if f"import {canonical_import} as _impl" not in module_text:
            failures.append(
                f"{package_name}: compatibility module must proxy {canonical_import}"
            )
        if "def __getattr__(name: str) -> object:" not in module_text:
            failures.append(
                f"{package_name}: compatibility module must proxy runtime attributes"
            )

    assert not failures, "\n".join(failures)
