"""Ensure no DeprecationWarnings escape from the core package."""

from __future__ import annotations

import importlib
import warnings

MODULES_TO_CHECK = (
    "bijux_canon_agent",
    "bijux_canon_agent.agents.base",
    "bijux_canon_agent.agents.planner",
    "bijux_canon_agent.agents.judge",
    "bijux_canon_agent.agents.verifier",
    "bijux_canon_agent.pipeline.pipeline",
    "bijux_canon_agent.pipeline.control.controller",
    "bijux_canon_agent.tracing.trace",
)


def test_no_deprecation_warnings() -> None:
    """Fail if any module under bijux_canon_agent emits a DeprecationWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        for module_name in MODULES_TO_CHECK:
            module = importlib.import_module(module_name)
            importlib.reload(module)
