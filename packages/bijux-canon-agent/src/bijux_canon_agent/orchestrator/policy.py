"""Failure and retry rules parsed from `packages/bijux-canon-agent/failure_policy.yaml`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

FAILURE_POLICY_RELATIVE_PATH = (
    Path("packages") / "bijux-canon-agent" / "failure_policy.yaml"
)
DEFAULT_TRANSIENT_CODES = ("TIMEOUT", "TRANSIENT")
DEFAULT_FALLBACK_MODELS = ("gpt-4o-mini", "gpt-4o-mini-0", "gpt-3.5-turbo-1106")
DEFAULT_SCOPE_REDUCTION_STEPS = (
    "collapse_documents",
    "summarize_sources",
    "reduce_to_key_points",
)
DEFAULT_CRITICAL_CODES = ("FATAL", "SECURITY")


@dataclass
class RetryPolicy:
    """Controls how many retries are allowed before failure."""

    max_attempts: int = 3
    transient_codes: list[str] = field(
        default_factory=lambda: list(DEFAULT_TRANSIENT_CODES)
    )


@dataclass
class ModelFallbackPolicy:
    """Declares a list of fallback models in preference order."""

    preferred_models: list[str] = field(
        default_factory=lambda: list(DEFAULT_FALLBACK_MODELS)
    )


@dataclass
class ScopeReductionPolicy:
    """Describes heuristic steps that reduce the scope of a task."""

    steps: list[str] = field(
        default_factory=lambda: list(DEFAULT_SCOPE_REDUCTION_STEPS)
    )


@dataclass
class AbortPolicy:
    """Defines when to abort the pipeline based on critical failures."""

    critical_codes: list[str] = field(
        default_factory=lambda: list(DEFAULT_CRITICAL_CODES)
    )
    max_errors_before_abort: int = 1


@dataclass
class FailurePolicy:
    """Aggregates retry/fallback/scope/abort behavior for the orchestrator."""

    retry: RetryPolicy = field(default_factory=RetryPolicy)
    fallback: ModelFallbackPolicy = field(default_factory=ModelFallbackPolicy)
    scope_reduction: ScopeReductionPolicy = field(default_factory=ScopeReductionPolicy)
    abort: AbortPolicy = field(default_factory=AbortPolicy)

    @staticmethod
    def default_path() -> Path:
        """Resolve the repository-managed failure policy path when available."""
        module_path = Path(__file__).resolve()
        for parent in module_path.parents:
            candidate = parent / FAILURE_POLICY_RELATIVE_PATH
            if candidate.is_file():
                return candidate
        return FAILURE_POLICY_RELATIVE_PATH

    @classmethod
    def load_default(cls) -> FailurePolicy:
        """Load the repository-managed failure policy or fall back to defaults."""
        return cls.load(cls.default_path())

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
