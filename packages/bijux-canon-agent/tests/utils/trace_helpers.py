from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from bijux_agent.constants import AGENT_CONTRACT_VERSION, CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.definition import (
    PipelineDefinition,
    standard_pipeline_definition,
)
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.tracing import (
    ReplayMetadata,
    RunFingerprint,
    RunTraceHeader,
    TraceEntry,
)
from bijux_agent.tracing.trace import ModelMetadata
from bijux_agent.utilities.prompt_hash import prompt_hash

DEFAULT_PIPELINE_DEFINITION: PipelineDefinition = standard_pipeline_definition()


def build_run_fingerprint(
    *,
    definition: PipelineDefinition | None = None,
    config: dict[str, Any] | None = None,
    contract_version: str = AGENT_CONTRACT_VERSION,
) -> RunFingerprint:
    return RunFingerprint.create(
        definition=definition or DEFAULT_PIPELINE_DEFINITION,
        config=config or {"mode": "test"},
        contract_version=contract_version,
    )


def default_model_metadata() -> ModelMetadata:
    return ModelMetadata(
        provider="test-provider",
        model_name="test-model",
        temperature=0.0,
        max_tokens=512,
    )


def build_replay_metadata(
    *,
    input_hash: str = "input-hash",
    config_hash: str = "config-hash",
    model_id: str = "model-id",
    convergence_hash: str = "trace-hash",
    contract_version: str = CONTRACT_VERSION,
    model_metadata: ModelMetadata | None = None,
) -> ReplayMetadata:
    return ReplayMetadata(
        input_hash=input_hash,
        config_hash=config_hash,
        model_id=model_id,
        convergence_hash=convergence_hash,
        contract_version=contract_version,
        model_metadata=model_metadata or default_model_metadata(),
    )


def build_trace_header(
    *,
    runtime_version: str = "test-runtime",
    convergence_hash: str = "trace-hash",
    convergence_reason: str = "stability",
    config_hash: str = "config-hash",
    pipeline_definition_hash: str = "definition-hash",
    agent_versions: dict[str, str] | None = None,
    model_metadata: ModelMetadata | None = None,
) -> RunTraceHeader:
    return RunTraceHeader(
        config_hash=config_hash,
        pipeline_definition_hash=pipeline_definition_hash,
        agent_versions=agent_versions or {"test-agent": "v0"},
        runtime_version=runtime_version,
        convergence_hash=convergence_hash,
        convergence_reason=convergence_reason,
        model_metadata=model_metadata or default_model_metadata(),
    )


def build_trace_entry(
    *,
    phase: PipelinePhase,
    run_id: str = "run-1",
    agent_id: str | None = None,
    node: str | None = None,
    status: str = "success",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    input_payload: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    scores: dict[str, float] | None = None,
    prompt_hash_value: str | None = None,
    model_hash: str | None = None,
    stop_reason: Any | None = None,
    failure_artifact: Any | None = None,
    run_fingerprint: RunFingerprint | None = None,
    replay_metadata: ReplayMetadata | None = None,
    decision_artifact: Any | None = None,
    epistemic_verdict: EpistemicVerdict | None = None,
    model_metadata: ModelMetadata | None = None,
    convergence_hash: str = "trace-hash",
) -> TraceEntry:
    now = datetime.now(UTC)
    start = start_time or now
    end = end_time or start
    model_meta = model_metadata or default_model_metadata()
    output = (
        dict(output_payload)
        if output_payload
        else {
            "text": f"{phase.value} result",
            "artifacts": {"phase": phase.value},
            "scores": {"quality": 0.95},
            "confidence": 0.9,
            "metadata": {
                "contract_version": CONTRACT_VERSION,
                "model_metadata": asdict(model_meta),
            },
            "decision": DecisionOutcome.PASS.value,
        }
    )
    metadata_section = dict(output.get("metadata", {}))
    metadata_section.setdefault("contract_version", CONTRACT_VERSION)
    metadata_section.setdefault("model_metadata", asdict(model_meta))
    output["metadata"] = metadata_section
    entry_replay_metadata = replay_metadata or build_replay_metadata(
        convergence_hash=convergence_hash
    )
    final_run_fingerprint = run_fingerprint or build_run_fingerprint()
    return TraceEntry(
        agent_id=agent_id or f"{phase.value}-agent",
        node=node or phase.value.lower(),
        status=status,
        start_time=start,
        end_time=end,
        input=input_payload or {"phase": phase.value},
        output=output,
        scores=scores or {"quality": 0.9},
        prompt_hash=prompt_hash_value or prompt_hash(f"{phase.value}:{run_id}"),
        model_hash=model_hash or f"{phase.value}-model-hash",
        phase=phase.value,
        run_id=run_id,
        stop_reason=stop_reason,
        failure_artifact=failure_artifact,
        replay_metadata=entry_replay_metadata,
        decision_artifact=decision_artifact,
        epistemic_verdict=epistemic_verdict,
        run_fingerprint=final_run_fingerprint,
    )
