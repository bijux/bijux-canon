"""Failure and retry rules parsed from `failure_policy.yaml`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RetryPolicy:
    """Controls how many retries are allowed before failure."""

    max_attempts: int = 3
    transient_codes: list[str] = field(default_factory=lambda: ["TIMEOUT", "TRANSIENT"])


@dataclass
class ModelFallbackPolicy:
    """Declares a list of fallback models in preference order."""

    preferred_models: list[str] = field(default_factory=list)


@dataclass
class ScopeReductionPolicy:
    """Describes heuristic steps that reduce the scope of a task."""

    steps: list[str] = field(
        default_factory=lambda: ["collapse_documents", "summaries_only"]
    )


@dataclass
class AbortPolicy:
    """Defines when to abort the pipeline based on critical failures."""

    critical_codes: list[str] = field(default_factory=lambda: ["FATAL"])
    max_errors_before_abort: int = 1


@dataclass
class FailurePolicy:
    """Aggregates retry/fallback/scope/abort behavior for the orchestrator."""

    retry: RetryPolicy = field(default_factory=RetryPolicy)
    fallback: ModelFallbackPolicy = field(default_factory=ModelFallbackPolicy)
    scope_reduction: ScopeReductionPolicy = field(default_factory=ScopeReductionPolicy)
    abort: AbortPolicy = field(default_factory=AbortPolicy)

    @classmethod
    def load(cls, path: Path | str) -> FailurePolicy:
        """Load overrides from a YAML policy file if it exists."""
        resolved = Path(path)
        if not resolved.is_file():
            return cls()
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
        return cls(
            retry=RetryPolicy(**raw.get("retry", {})),
            fallback=ModelFallbackPolicy(**raw.get("fallback", {})),
            scope_reduction=ScopeReductionPolicy(**raw.get("scope_reduction", {})),
            abort=AbortPolicy(**raw.get("abort", {})),
        )
