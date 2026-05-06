from __future__ import annotations

from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPATIBILITY_TARGETS = {
    "compat-agentic-flows": "bijux_canon_runtime",
    "compat-bijux-agent": "bijux_canon_agent",
    "compat-bijux-rag": "bijux_canon_ingest",
    "compat-bijux-rar": "bijux_canon_reason",
    "compat-bijux-vex": "bijux_canon_index",
}


def _workspace_metadata() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["bijux_canon"]


def test_compatibility_packages_are_explicitly_tracked_in_workspace_metadata() -> None:
    workspace = _workspace_metadata()

    assert set(workspace["compat_packages"]) == set(COMPATIBILITY_TARGETS)


def test_compatibility_packages_remain_test_exempt_only_while_they_stay_thin() -> None:
    failures: list[str] = []

    for package_name, canonical_import in COMPATIBILITY_TARGETS.items():
        package_root = REPO_ROOT / "packages" / package_name
        tests_dir = package_root / "tests"
        if tests_dir.exists():
            failures.append(f"{package_name}: compatibility packages must not grow ad hoc tests")

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
            failures.append(f"{package_name}: compatibility module must proxy runtime attributes")

    assert not failures, "\n".join(failures)
