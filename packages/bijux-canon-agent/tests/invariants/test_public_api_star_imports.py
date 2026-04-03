"""Invariant: public modules expose only their __all__ via star import."""

from __future__ import annotations

import importlib

PUBLIC_MODULES = {
    "bijux_canon_agent": ("API_VERSION",),
    "bijux_canon_agent.agents": (
        "CritiqueAgent",
        "FileReaderAgent",
        "PlannerAgent",
        "SummarizerAgent",
        "WorkflowExecutorAgent",
        "ValidatorAgent",
        "JudgeAgent",
        "VerifierAgent",
    ),
    "bijux_canon_agent.pipeline": (
        "AuditableDocPipeline",
        "Pipeline",
        "PipelineDefinition",
    ),
    "bijux_canon_agent.examples": (
        "MinimalPipeline",
        "run_minimal",
        "DocumentReviewPipeline",
        "run_document_review",
    ),
}


def _star_imported(module_name: str) -> set[str]:
    namespace: dict[str, object] = {"__builtins__": __builtins__}
    exec(f"from {module_name} import *", namespace)  # noqa: S102 - invariant test for star imports
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
