from __future__ import annotations

import importlib

LEGACY_MODULE_NAME = "agentic_flows"
CANONICAL_MODULE_NAME = "bijux_canon_runtime"
LEGACY_SUBMODULE_NAME = "agentic_flows.interfaces.cli.entrypoint"
CANONICAL_SUBMODULE_NAME = "bijux_canon_runtime.interfaces.cli.entrypoint"
ROOT_EXPORTS = ("FlowManifest", "RunMode", "execute_flow")


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
