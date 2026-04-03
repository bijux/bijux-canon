"""Snapshot test guarding the public API surface from accidental change."""

from __future__ import annotations

import importlib

MODULE_SNAPSHOT = {
    "bijux_canon_agent": ("API_VERSION",),
    "bijux_canon_agent.agents": (
        "CritiqueAgent",
        "FileReaderAgent",
        "PlannerAgent",
        "SummarizerAgent",
        "StageRunnerAgent",
        "ValidatorAgent",
        "JudgeAgent",
        "VerifierAgent",
    ),
    "bijux_canon_agent.pipeline": (
        "AuditableDocPipeline",
        "Pipeline",
        "PipelineDefinition",
    ),
    "bijux_canon_agent.reference_pipelines": (
        "MinimalPipeline",
        "run_minimal",
        "DocumentReviewPipeline",
        "run_document_review",
    ),
}


def test_public_api_snapshot() -> None:
    """Fail if any facade drops __all__ entries or critical exports."""
    actual = {}
    for module_name, expected in MODULE_SNAPSHOT.items():
        module = importlib.import_module(module_name)
        exports = tuple(getattr(module, "__all__", ()))
        actual[module_name] = exports
        assert exports == expected, (
            f"{module_name} __all__ changed: expected {expected}, got {exports}"
        )
    assert actual == MODULE_SNAPSHOT

    critical_map = {
        "CritiqueAgent": "bijux_canon_agent.agents",
        "SummarizerAgent": "bijux_canon_agent.agents",
        "Pipeline": "bijux_canon_agent.pipeline",
        "PipelineDefinition": "bijux_canon_agent.pipeline",
    }
    for class_name, module_name in critical_map.items():
        module = importlib.import_module(module_name)
        assert hasattr(module, class_name), f"{class_name} missing from {module_name}"
