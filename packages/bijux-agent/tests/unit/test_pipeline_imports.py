"""Block regressions that pull heavy modules into the pipeline surface."""

from __future__ import annotations

import importlib
import sys

RESTRICTED_PREFIXES = (
    "bijux_agent.agents",
    "bijux_agent.utilities",
    "bijux_agent.agents.file_reader.capabilities",
)


def _collect_prefixed_modules(prefix: str) -> set[str]:
    return {name for name in sys.modules if name.startswith(prefix)}


def test_pipeline_imports_only_core() -> None:
    """Ensure importing bijux_agent.pipeline does not import external helpers."""
    baseline = {
        prefix: _collect_prefixed_modules(prefix) for prefix in RESTRICTED_PREFIXES
    }
    sys.modules.pop("bijux_agent.pipeline", None)
    importlib.import_module("bijux_agent.pipeline")
    for prefix in RESTRICTED_PREFIXES:
        current = _collect_prefixed_modules(prefix)
        assert current == baseline[prefix], (
            f"Pipeline import pulled in {current - baseline[prefix]} for {prefix}"
        )
