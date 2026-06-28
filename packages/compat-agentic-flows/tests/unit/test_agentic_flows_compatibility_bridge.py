from __future__ import annotations

import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[3] / "bijux-canon-runtime" / "src"),
)

LEGACY_MODULE_NAME = "agentic_flows"
CANONICAL_MODULE_NAME = "bijux_canon_runtime"
LEGACY_SUBMODULE_NAME = "agentic_flows.interfaces.cli.entrypoint"
CANONICAL_SUBMODULE_NAME = "bijux_canon_runtime.interfaces.cli.entrypoint"
LEGACY_NESTED_MODULE_NAME = "agentic_flows.model.flows.manifest"
CANONICAL_NESTED_MODULE_NAME = "bijux_canon_runtime.model.flows.manifest"
ROOT_EXPORTS = ("FlowManifest",)


def test_legacy_package_root_exports_match_canonical_package() -> None:
    legacy = importlib.import_module(LEGACY_MODULE_NAME)
    canonical = importlib.import_module(CANONICAL_MODULE_NAME)

    assert legacy.__all__ == canonical.__all__
    for export_name in ROOT_EXPORTS:
        assert export_name in dir(legacy)
        assert getattr(legacy, export_name) == getattr(canonical, export_name)


def test_legacy_package_root_import_stays_lazy() -> None:
    sys.modules.pop(LEGACY_MODULE_NAME, None)
    sys.modules.pop("bijux_canon_runtime.application.execute_flow", None)
    sys.modules.pop(
        "bijux_canon_runtime.observability.storage.execution_store",
        None,
    )

    legacy = importlib.import_module(LEGACY_MODULE_NAME)

    assert legacy.__name__ == LEGACY_MODULE_NAME
    assert "bijux_canon_runtime.application.execute_flow" not in sys.modules
    assert (
        "bijux_canon_runtime.observability.storage.execution_store" not in sys.modules
    )


def test_legacy_package_cli_module_aliases_canonical_module_identity() -> None:
    legacy_cli = importlib.import_module(LEGACY_SUBMODULE_NAME)
    canonical_cli = importlib.import_module(CANONICAL_SUBMODULE_NAME)

    assert legacy_cli is canonical_cli


def test_nested_runtime_types_keep_identity_under_alias_imports() -> None:
    legacy_module = importlib.import_module(LEGACY_NESTED_MODULE_NAME)
    canonical_module = importlib.import_module(CANONICAL_NESTED_MODULE_NAME)

    assert legacy_module.FlowManifest is canonical_module.FlowManifest
