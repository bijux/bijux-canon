from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_PYPROJECT = REPO_ROOT / "pyproject.toml"

COMPATIBILITY_PACKAGES = {
    "compat-bijux-canon": {
        "distribution": "bijux-canon",
        "module": "bijux_canon",
        "runtime": "bijux_canon_runtime",
        "script": "bijux-canon",
    },
    "compat-agentic-flows": {
        "distribution": "agentic-flows",
        "module": "agentic_flows",
        "runtime": "bijux_canon_runtime",
        "script": "agentic-flows",
    },
    "compat-bijux-agent": {
        "distribution": "bijux-agent",
        "module": "bijux_agent",
        "runtime": "bijux_canon_agent",
        "script": "bijux-agent",
    },
    "compat-bijux-rag": {
        "distribution": "bijux-rag",
        "module": "bijux_rag",
        "runtime": "bijux_canon_ingest",
        "script": "bijux-rag",
    },
    "compat-bijux-rar": {
        "distribution": "bijux-rar",
        "module": "bijux_rar",
        "runtime": "bijux_canon_reason",
        "script": "bijux-rar",
    },
    "compat-bijux-vex": {
        "distribution": "bijux-vex",
        "module": "bijux_vex",
        "runtime": "bijux_canon_index",
        "script": "bijux-vex",
    },
}


def _workspace_metadata() -> dict[str, Any]:
    with WORKSPACE_PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    return cast(dict[str, Any], data["tool"]["bijux_canon"])


def _package_root(package_name: str) -> Path:
    workspace = _workspace_metadata()
    package_dirs = cast(dict[str, str], workspace["package_dirs"])
    return REPO_ROOT / package_dirs[package_name]


def test_workspace_metadata_declares_all_compatibility_packages() -> None:
    workspace = _workspace_metadata()
    compat_packages = cast(list[str], workspace["compat_packages"])

    assert compat_packages == [
        "compat-bijux-canon",
        "compat-agentic-flows",
        "compat-bijux-agent",
        "compat-bijux-rag",
        "compat-bijux-rar",
        "compat-bijux-vex",
    ]


def test_compatibility_packages_keep_runtime_alias_layout() -> None:
    failures: list[str] = []

    for package_name, expectation in COMPATIBILITY_PACKAGES.items():
        package_root = _package_root(package_name)
        module_name = expectation["module"]
        module_root = package_root / "src" / module_name
        test_path = (
            package_root
            / "tests"
            / "unit"
            / f"test_{module_name}_compatibility_bridge.py"
        )

        for required_path in (
            package_root / "README.md",
            package_root / "CHANGELOG.md",
            package_root / "overview.md",
            package_root / "hatch_build.py",
            module_root / "__init__.py",
            module_root / "__main__.py",
            module_root / "runtime_alias.py",
            module_root / "py.typed",
            test_path,
        ):
            if not required_path.exists():
                failures.append(
                    f"{package_name}: missing {required_path.relative_to(package_root)}"
                )

    assert not failures, "compatibility package layout failed:\n" + "\n".join(failures)


def test_compatibility_packages_install_runtime_alias_helpers() -> None:
    failures: list[str] = []

    for package_name, expectation in COMPATIBILITY_PACKAGES.items():
        package_root = _package_root(package_name)
        module_name = expectation["module"]
        runtime_name = expectation["runtime"]
        init_text = (package_root / "src" / module_name / "__init__.py").read_text(
            encoding="utf-8"
        )
        runtime_alias_text = (
            package_root / "src" / module_name / "runtime_alias.py"
        ).read_text(encoding="utf-8")
        main_text = (package_root / "src" / module_name / "__main__.py").read_text(
            encoding="utf-8"
        )

        expected_init_fragments = (
            "install_runtime_aliases",
            f'_ALIAS_PACKAGE = "{module_name}"',
            f'_RUNTIME_PACKAGE = "{runtime_name}"',
            "__getattr__",
            "__dir__",
        )
        for fragment in expected_init_fragments:
            if fragment not in init_text:
                failures.append(f"{package_name}: __init__.py missing {fragment!r}")

        for fragment in (
            "class _RuntimeAliasLoader",
            "class _RuntimeAliasFinder",
            "def install_runtime_aliases",
        ):
            if fragment not in runtime_alias_text:
                failures.append(
                    f"{package_name}: runtime_alias.py missing {fragment!r}"
                )

        if f"from {runtime_name}.interfaces.cli" not in main_text:
            failures.append(
                f"{package_name}: __main__.py should import its CLI from the canonical package"
            )
        if 'if __name__ == "__main__":' not in main_text:
            failures.append(
                f"{package_name}: __main__.py should dispatch the canonical CLI directly"
            )

    assert not failures, "runtime alias helper contract failed:\n" + "\n".join(failures)
