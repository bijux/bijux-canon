"""Invariant: public modules expose only their __all__ via star import."""

from __future__ import annotations

import importlib

PUBLIC_MODULES = {
    "bijux_agent": ("API_VERSION",),
    "bijux_agent.agents": (
        "CritiqueAgent",
        "FileReaderAgent",
        "PlannerAgent",
        "SummarizerAgent",
        "TaskHandlerAgent",
        "ValidatorAgent",
        "JudgeAgent",
        "VerifierAgent",
    ),
    "bijux_agent.pipeline": (
        "AuditableDocPipeline",
        "Pipeline",
        "PipelineDefinition",
    ),
    "bijux_agent.reference": (
        "MinimalPipeline",
        "run_minimal",
        "DocumentReviewPipeline",
        "run_document_review",
    ),
}


def _star_imported(module_name: str) -> set[str]:
    namespace: dict[str, object] = {"__builtins__": __builtins__}
    exec(f"from {module_name} import *", namespace)
    namespace.pop("__builtins__", None)
    return set(namespace.keys())


def test_public_star_imports_match_all() -> None:
    for module_name, expected in PUBLIC_MODULES.items():
        module = importlib.import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        assert exports == expected, (
            f"{module_name} __all__ changed: expected {expected}, got {exports}"
        )
        assert _star_imported(module_name) == set(expected), (
            f"{module_name} star import drifted from __all__"
        )
