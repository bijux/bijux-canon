from __future__ import annotations

import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[3] / "bijux-canon-reason" / "src"),
)

LEGACY_MODULE_NAME = "bijux_rar"
CANONICAL_MODULE_NAME = "bijux_canon_reason"
LEGACY_SUBMODULE_NAME = "bijux_rar.interfaces.cli"
CANONICAL_SUBMODULE_NAME = "bijux_canon_reason.interfaces.cli"
LEGACY_NESTED_MODULE_NAME = "bijux_rar.core"
CANONICAL_NESTED_MODULE_NAME = "bijux_canon_reason.core"
ROOT_EXPORTS = ("__version__", "Claim", "validate_plan")


def test_legacy_package_root_exports_match_canonical_package() -> None:
    legacy = importlib.import_module(LEGACY_MODULE_NAME)
    canonical = importlib.import_module(CANONICAL_MODULE_NAME)

    assert legacy.__all__ == canonical.__all__
    for export_name in ROOT_EXPORTS:
        assert export_name in dir(legacy)
        assert getattr(legacy, export_name) == getattr(canonical, export_name)


def test_legacy_package_cli_module_aliases_canonical_module_identity() -> None:
    legacy_cli = importlib.import_module(LEGACY_SUBMODULE_NAME)
    canonical_cli = importlib.import_module(CANONICAL_SUBMODULE_NAME)

    assert legacy_cli is canonical_cli


def test_nested_runtime_types_keep_identity_under_alias_imports() -> None:
    legacy_module = importlib.import_module(LEGACY_NESTED_MODULE_NAME)
    canonical_module = importlib.import_module(CANONICAL_NESTED_MODULE_NAME)

    assert legacy_module.Claim is canonical_module.Claim
