from __future__ import annotations

import importlib

LEGACY_MODULE_NAME = "bijux_rar"
CANONICAL_MODULE_NAME = "bijux_canon_reason"
LEGACY_SUBMODULE_NAME = "bijux_rar.interfaces.cli"
CANONICAL_SUBMODULE_NAME = "bijux_canon_reason.interfaces.cli"
ROOT_EXPORTS = ("__version__", "Claim", "validate_plan")


def test_legacy_package_root_exports_match_canonical_package() -> None:
    legacy = importlib.import_module(LEGACY_MODULE_NAME)
    canonical = importlib.import_module(CANONICAL_MODULE_NAME)

    assert list(legacy.__path__) == list(canonical.__path__)
    for export_name in ROOT_EXPORTS:
        assert export_name in dir(legacy)
        assert getattr(legacy, export_name) == getattr(canonical, export_name)


def test_legacy_package_cli_module_resolves_from_canonical_path() -> None:
    legacy_cli = importlib.import_module(LEGACY_SUBMODULE_NAME)
    canonical_cli = importlib.import_module(CANONICAL_SUBMODULE_NAME)

    assert legacy_cli.__file__ == canonical_cli.__file__
