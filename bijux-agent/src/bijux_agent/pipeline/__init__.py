"""
Pipeline package.

IMPORTANT: keep this module import-light.
Importing submodules here can create circular imports when other packages import
`bijux_agent.pipeline.<submodule>` (Python executes this `__init__` first).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Keep __all__ stable (tests snapshot it).
__all__ = [
    "AuditableDocPipeline",
    "Pipeline",
    "PipelineDefinition",
]

if TYPE_CHECKING:
    from .canonical import AuditableDocPipeline
    from .definition import PipelineDefinition
    from .pipeline import Pipeline


def __getattr__(name: str) -> Any:
    if name == "Pipeline":
        from .pipeline import Pipeline

        return Pipeline
    if name == "AuditableDocPipeline":
        from .canonical import AuditableDocPipeline

        return AuditableDocPipeline
    if name == "PipelineDefinition":
        from .definition import PipelineDefinition

        return PipelineDefinition
    # Not part of the public facade (__all__), but still accessible.
    if name == "standard_pipeline_definition":
        from .definition import standard_pipeline_definition

        return standard_pipeline_definition
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
