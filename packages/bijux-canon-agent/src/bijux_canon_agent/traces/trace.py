"""Serialization helpers for storing structured agent call graphs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from pathlib import Path
from typing import Any, ClassVar

from bijux_canon_agent.constants import AGENT_CONTRACT_VERSION, CONTRACT_VERSION
from bijux_canon_agent.core.version import get_runtime_version
from bijux_canon_agent.pipeline.control.stop_conditions import StopReason
from bijux_canon_agent.pipeline.definition import PipelineDefinition
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict
from bijux_canon_agent.pipeline.results.decision import DecisionArtifact
from bijux_canon_agent.pipeline.results.failure import FailureArtifact
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason
from bijux_canon_agent.traces.replayability import (
    enforce_replayable_temperature,
    has_required_replay_metadata,
    resolve_contract_version,
)
from bijux_canon_agent.traces.trace_serialization import (
    serialize_run_trace,
    serialize_trace_entry,
    serialize_value,
)


class TraceFieldClassification(StrEnum):
    DETERMINISTIC = "deterministic"
    OBSERVATIONAL = "observational"


TRACE_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ModelMetadata:
    """Structured metadata describing the model used in a trace."""

    provider: str
    model_name: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ModelMetadata:
        if not data:
            raise RuntimeError("Model metadata cannot be empty")
        try:
            provider = str(data["provider"])
            model_name = str(data["model_name"])
            temperature = float(data["temperature"])
            max_tokens = int(data["max_tokens"])
        except KeyError as exc:
            raise RuntimeError(f"Model metadata missing {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Model metadata fields must be numeric") from exc
        return cls(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )


@dataclass
class RunFingerprint:
    pipeline_definition: dict[str, Any]
    agent_contract_version: str
    config_snapshot: dict[str, Any]
    fingerprint: str

    @classmethod
    def create(
        cls,
        definition: PipelineDefinition,
        config: Mapping[str, Any],
        contract_version: str = AGENT_CONTRACT_VERSION,
    ) -> RunFingerprint:
        definition_payload = {
            "name": definition.name,
            "phases": [phase.value for phase in definition.phases],
            "terminal_phases": sorted(
                [phase.value for phase in definition.terminal_phases]
            ),
            "allowed_transitions": {
                phase.value: sorted([target.value for target in targets])
                for phase, targets in definition.allowed_transitions.items()
            },
            "skip_reasons": {
                phase.value: reason for phase, reason in definition.skip_reasons.items()
            },
        }
        payload = json.dumps(
            {
                "definition": definition_payload,
                "contract_version": contract_version,
                "config": config,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        hashed = hashlib.sha256(payload.encode()).hexdigest()
        return RunFingerprint(
            pipeline_definition=definition_payload,
            agent_contract_version=contract_version,
            config_snapshot=dict(config),
            fingerprint=hashed,
        )


class ReplayStatus(StrEnum):
    """Replayability states recorded in trace headers."""

    REPLAYABLE = "REPLAYABLE"
    NON_REPLAYABLE = "NON_REPLAYABLE"


@dataclass
class RunTraceHeader:
    """Captured metadata describing the pipeline run."""

    trace_schema_version: int = TRACE_SCHEMA_VERSION
    config_hash: str = ""
    pipeline_definition_hash: str = ""
    agent_versions: dict[str, str] = field(default_factory=dict)
    replay_status: ReplayStatus = field(default_factory=lambda: ReplayStatus.REPLAYABLE)
    runtime_version: str = field(default_factory=get_runtime_version)
    convergence_hash: str = ""
    convergence_reason: str | None = None
    termination_reason: ExecutionTerminationReason = field(
        default_factory=lambda: ExecutionTerminationReason.COMPLETED
    )
    model_metadata: ModelMetadata | None = None


@dataclass
class ReplayMetadata:
    """Immutable metadata used for deterministic replay."""

    input_hash: str = ""
    config_hash: str = ""
    model_id: str = ""
    convergence_hash: str = ""
    contract_version: str = CONTRACT_VERSION
    model_metadata: ModelMetadata | None = None


@dataclass
class EpistemicStatus:
    """Structured artifact describing epistemic certainty."""

    status: str
    justification: str


@dataclass
class TraceEntry:
    agent_id: str
    node: str
    status: str
    start_time: datetime
    end_time: datetime
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    scores: dict[str, float] = field(default_factory=dict)
    prompt_hash: str = ""
    model_hash: str = ""
    phase: str | None = None
    run_id: str | None = None
    stop_reason: StopReason | None = None
    failure_artifact: FailureArtifact | None = None
    replay_metadata: ReplayMetadata = field(default_factory=ReplayMetadata)
    epistemic_status: EpistemicStatus | None = None
    epistemic_verdict: EpistemicVerdict | None = None
    decision_artifact: DecisionArtifact | None = None
    run_fingerprint: RunFingerprint | None = None
    termination_reason: ExecutionTerminationReason | None = None
    FIELD_CLASSIFICATIONS: ClassVar[dict[str, TraceFieldClassification]] = {
        "start_time": TraceFieldClassification.OBSERVATIONAL,
        "end_time": TraceFieldClassification.OBSERVATIONAL,
    }

    @classmethod
    def observational_fields(cls) -> set[str]:
        return {
            name
            for name, classification in cls.FIELD_CLASSIFICATIONS.items()
            if classification == TraceFieldClassification.OBSERVATIONAL
        }

    def deterministic_snapshot(self) -> dict[str, Any]:
        data = self.to_dict()
        observational = self.observational_fields()
        return {key: value for key, value in data.items() if key not in observational}

    def to_dict(self) -> dict[str, Any]:
        return serialize_trace_entry(self)


@dataclass
class RunTrace:
    run_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"
    header: RunTraceHeader = field(default_factory=RunTraceHeader)
    entries: list[TraceEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return serialize_run_trace(self)


class TraceRecorder:
    def __init__(
        self,
        run_id: str,
        path: Path | str,
        config_hash: str | None = None,
        pipeline_definition_hash: str | None = None,
        agent_versions: Mapping[str, str] | None = None,
        runtime_version: str | None = None,
        convergence_hash: str | None = None,
        convergence_reason: str | None = None,
        termination_reason: ExecutionTerminationReason | None = None,
        model_metadata: ModelMetadata | None = None,
    ):
        resolved_runtime = runtime_version or get_runtime_version()
        header = RunTraceHeader(
            config_hash=config_hash or "",
            pipeline_definition_hash=pipeline_definition_hash or "",
            agent_versions=dict(agent_versions or {}),
            runtime_version=resolved_runtime,
            convergence_hash=convergence_hash or "",
            convergence_reason=convergence_reason,
            termination_reason=termination_reason
            or ExecutionTerminationReason.COMPLETED,
            model_metadata=model_metadata,
        )
        self.trace = RunTrace(run_id=run_id, header=header)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_entry(self, entry: TraceEntry) -> None:
        """Record the given trace entry while enforcing trace-level metadata."""
        entry.run_id = self.trace.run_id
        metadata: dict[str, Any] = {}
        if isinstance(entry.output, dict):
            metadata = entry.output.get("metadata", {})
        entry.replay_metadata.contract_version = resolve_contract_version(metadata)
        model_metadata = self._extract_model_metadata(metadata)
        if model_metadata:
            if (
                self.trace.header.model_metadata
                and self.trace.header.model_metadata != model_metadata
            ):
                raise RuntimeError("Conflicting model metadata recorded in trace")
            self.trace.header.model_metadata = (
                self.trace.header.model_metadata or model_metadata
            )
            entry.replay_metadata.model_metadata = self.trace.header.model_metadata
            if model_metadata.temperature > 0:
                self.trace.header.replay_status = ReplayStatus.NON_REPLAYABLE
        elif self.trace.header.model_metadata:
            entry.replay_metadata.model_metadata = self.trace.header.model_metadata
        else:
            raise RuntimeError(
                "Trace entry missing model metadata required for deterministic trace"
            )
        if entry.termination_reason is None:
            entry.termination_reason = self.trace.header.termination_reason
        if self.trace.header.convergence_hash:
            entry.replay_metadata.convergence_hash = self.trace.header.convergence_hash
        if not has_required_replay_metadata(
            entry.replay_metadata,
            phase=entry.phase,
            convergence_hash=self.trace.header.convergence_hash,
        ):
            self.trace.header.replay_status = ReplayStatus.NON_REPLAYABLE
        self._enforce_replayability()
        self.trace.entries.append(entry)

    @staticmethod
    def _extract_model_metadata(
        metadata: Mapping[str, Any] | None,
    ) -> ModelMetadata | None:
        if not metadata:
            return None
        raw = metadata.get("model_metadata")
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise RuntimeError("model_metadata must be a mapping")
        return ModelMetadata.from_mapping(raw)

    def _enforce_replayability(self) -> None:
        metadata = self.trace.header.model_metadata
        if not metadata:
            return
        enforce_replayable_temperature(
            temperature=metadata.temperature,
            replayable=self.trace.header.replay_status == ReplayStatus.REPLAYABLE,
        )

    def finish(self, status: str = "completed") -> None:
        self.trace.status = status
        self.trace.completed_at = datetime.now(UTC)
        self._write()

    def _write(self) -> None:
        if self.trace.header.model_metadata is None:
            raise RuntimeError("Trace header must include model metadata")
        self._enforce_replayability()
        self.path.write_text(
            json.dumps(
                self.trace.to_dict(),
                indent=2,
                default=serialize_value,
            ),
            encoding="utf-8",
        )
