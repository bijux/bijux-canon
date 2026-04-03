from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest
from tests.utils.trace_helpers import (
    build_replay_metadata,
    build_run_fingerprint,
    build_trace_header,
    default_model_metadata,
)

from bijux_agent.constants import AGENT_CONTRACT_VERSION, CONTRACT_VERSION
from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.pipeline.control.controller import PipelineController
from bijux_agent.pipeline.control.phases import PHASE_SEQUENCE, PipelinePhase
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceConfig,
    ConvergenceMonitor,
    ConvergenceReason,
)
from bijux_agent.pipeline.definition import (
    PipelineDefinition,
    standard_pipeline_definition,
)
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.execution.interrupt import InterruptMonitor
from bijux_agent.pipeline.results.decision import DecisionArtifact
from bijux_agent.pipeline.results.failure import (
    FailureArtifact,
    FailureCategory,
    FailureClass,
)
from bijux_agent.pipeline.results.outcome import PipelineResult, PipelineStatus
from bijux_agent.pipeline.tracing.trace_validator import TraceValidator
from bijux_agent.tracing import (
    ReplayMetadata,
    RunFingerprint,
    RunTrace,
    RunTraceHeader,
    TraceEntry,
    TraceRecorder,
)
from bijux_agent.utilities.prompt_hash import prompt_hash

STANDARD_TRANSITIONS = [
    (PipelinePhase.PLAN, AgentType.PLANNER),
    (PipelinePhase.EXECUTE, AgentType.SUMMARIZER),
    (PipelinePhase.JUDGE, AgentType.JUDGE),
    (PipelinePhase.VERIFY, AgentType.VERIFIER),
    (PipelinePhase.FINALIZE, AgentType.ORCHESTRATOR),
]

CANONICAL_DEFINITION = standard_pipeline_definition()


def _test_header() -> RunTraceHeader:
    return build_trace_header(
        runtime_version="test-runtime",
        convergence_hash="trace-hash",
        convergence_reason=ConvergenceReason.STABILITY.value,
    )


def _build_run_fingerprint(contract_version: str | None = None) -> RunFingerprint:
    return RunFingerprint.create(
        definition=CANONICAL_DEFINITION,
        config={"mode": "test"},
        contract_version=contract_version or AGENT_CONTRACT_VERSION,
    )


def _default_decision_artifact(
    verdict: DecisionOutcome = DecisionOutcome.PASS,
) -> DecisionArtifact:
    return DecisionArtifact(
        verdict=verdict,
        justification="pipeline level verdict",
        supporting_trace_ids=[],
    )


def _build_entry(
    agent_type: AgentType,
    phase: PipelinePhase,
    stop_reason: StopReason | None = None,
    run_id: str = "test-run",
    failure_artifact: FailureArtifact | None = None,
    epistemic_verdict: EpistemicVerdict | None = None,
    run_fingerprint: RunFingerprint | None = None,
    decision_artifact: DecisionArtifact | None = None,
    attach_decision_artifact: bool = True,
    convergence_hash: str | None = None,
) -> TraceEntry:
    now = datetime.now(UTC)
    resolved_verdict = epistemic_verdict
    if resolved_verdict is None and phase == PipelinePhase.FINALIZE:
        resolved_verdict = EpistemicVerdict.CERTAIN
    resolved_artifact = decision_artifact
    if (
        resolved_artifact is None
        and phase == PipelinePhase.FINALIZE
        and attach_decision_artifact
    ):
        resolved_artifact = _default_decision_artifact()
    resolved_run_fingerprint = run_fingerprint
    if (
        phase in (PipelinePhase.FINALIZE, PipelinePhase.ABORTED)
        and resolved_run_fingerprint is None
    ):
        resolved_run_fingerprint = _build_run_fingerprint()
    final_convergence_hash = convergence_hash
    if phase == PipelinePhase.FINALIZE and not convergence_hash:
        final_convergence_hash = "trace-hash"
    metadata_repr = ReplayMetadata(
        input_hash=f"{phase.value}-input",
        config_hash="test-config",
        model_id=agent_type.value,
        convergence_hash=final_convergence_hash
        if phase == PipelinePhase.FINALIZE
        else "",
    )
    return TraceEntry(
        agent_id=agent_type.name,
        node=agent_type.value,
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": phase.value, "agent_type": agent_type.value},
        output={
            "text": f"{phase.value} result",
            "artifacts": {"phase": phase.value},
            "scores": {"quality": 0.95},
            "confidence": 0.9,
            "metadata": {"contract_version": CONTRACT_VERSION},
            "decision": DecisionOutcome.PASS.value,
        },
        scores={"quality": 0.95},
        prompt_hash=prompt_hash(f"{phase.value}:{run_id}"),
        model_hash=hashlib.sha256(agent_type.value.encode()).hexdigest(),
        phase=phase.value,
        run_id=run_id,
        stop_reason=stop_reason,
        failure_artifact=failure_artifact,
        replay_metadata=metadata_repr,
        epistemic_verdict=resolved_verdict,
        decision_artifact=resolved_artifact,
        run_fingerprint=resolved_run_fingerprint,
    )


def _build_standard_entries(
    run_id: str, fingerprint: RunFingerprint
) -> list[TraceEntry]:
    return [
        _build_entry(
            agent_type,
            phase,
            run_id=run_id,
            run_fingerprint=fingerprint if phase == PipelinePhase.FINALIZE else None,
            convergence_hash="trace-hash" if phase == PipelinePhase.FINALIZE else None,
        )
        for phase, agent_type in STANDARD_TRANSITIONS
    ]


def _standard_convergence_monitor() -> ConvergenceMonitor:
    monitor = ConvergenceMonitor(
        config=ConvergenceConfig(
            epsilon=1e-3,
            identical_verdicts=2,
            confidence_tolerance=0.01,
            window_size=3,
        )
    )
    for scores, verdict, confidence in [
        ({"score": 0.6}, DecisionOutcome.PASS, 0.95),
        ({"score": 0.65}, DecisionOutcome.PASS, 0.96),
        ({"score": 0.7}, DecisionOutcome.PASS, 0.97),
    ]:
        monitor.record(scores, verdict, confidence)
    return monitor


def _trace_from_entries(
    run_id: str,
    entries: list[TraceEntry],
    status: str = "completed",
    header: RunTraceHeader | None = None,
) -> RunTrace:
    trace = RunTrace(run_id=run_id, status=status, header=header or _test_header())
    trace.entries.extend(entries)
    return trace


def test_pipeline_transitions_and_trace_validation() -> None:
    controller = PipelineController()
    entries: list[TraceEntry] = []
    run_fingerprint = _build_run_fingerprint()

    for phase, agent_type in STANDARD_TRANSITIONS:
        controller.transition_to(phase)
        controller._align_agent(agent_type)
        entries.append(
            _build_entry(
                agent_type,
                phase,
                run_id="run-1",
                run_fingerprint=run_fingerprint
                if phase == PipelinePhase.FINALIZE
                else None,
            )
        )

    controller.record_outcome(DecisionOutcome.PASS, 0.92)
    entries[-1].output["confidence"] = 0.92
    trace = _trace_from_entries("run-1", entries, status="completed")
    outcome = controller.finalize(trace)

    metadata = trace.header.model_metadata
    assert metadata is not None

    expected = PipelineResult(
        status=PipelineStatus.DONE,
        decision=DecisionOutcome.APPROVE,
        epistemic_verdict=EpistemicVerdict.CERTAIN,
        confidence=0.92,
        model_metadata=metadata,
    )
    assert outcome == expected
    assert controller.phase == PipelinePhase.DONE
    assert controller.history == [
        PipelinePhase.INIT,
        PipelinePhase.PLAN,
        PipelinePhase.EXECUTE,
        PipelinePhase.JUDGE,
        PipelinePhase.VERIFY,
        PipelinePhase.FINALIZE,
        PipelinePhase.DONE,
    ]

    TraceValidator.validate(
        entries,
        CANONICAL_DEFINITION,
        stop_reason=None,
        header=_test_header(),
    )


def test_finalize_returns_pipeline_result_object() -> None:
    controller = PipelineController()
    for phase, _ in STANDARD_TRANSITIONS:
        controller.transition_to(phase)
    controller.record_outcome(DecisionOutcome.PASS, 0.85)
    entry = _build_entry(
        AgentType.ORCHESTRATOR,
        PipelinePhase.FINALIZE,
        run_id="finalize-run",
    )
    trace = _trace_from_entries("finalize-run", [entry], status="completed")
    outcome = controller.finalize(trace)
    assert isinstance(outcome, PipelineResult)


def test_pipeline_controller_done_transition_requires_finalize() -> None:
    controller = PipelineController()
    controller.transition_to(PipelinePhase.PLAN)
    controller.transition_to(PipelinePhase.EXECUTE)
    controller.transition_to(PipelinePhase.JUDGE)
    controller.transition_to(PipelinePhase.VERIFY)
    with pytest.raises(RuntimeError):
        controller.transition_to(PipelinePhase.DONE)
    controller.transition_to(PipelinePhase.FINALIZE)
    controller.transition_to(PipelinePhase.DONE)


def test_pipeline_golden_trace(test_artifacts_dir: Path) -> None:
    trace_path = test_artifacts_dir / "golden_trace.json"
    recorder = TraceRecorder(
        run_id="golden-run",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    phases = [
        phase
        for phase in CANONICAL_DEFINITION.phases
        if phase not in (PipelinePhase.INIT, PipelinePhase.DONE)
    ]
    confidences = [0.8 + idx * 0.02 for idx in range(len(phases))]

    for idx, phase in enumerate(phases):
        entry = TraceEntry(
            agent_id=f"{phase.value}-agent",
            node=phase.value.lower(),
            status="success",
            start_time=base_time + timedelta(minutes=idx),
            end_time=base_time + timedelta(minutes=idx, seconds=30),
            input={"phase": phase.value},
            output={
                "text": f"{phase.value} result",
                "artifacts": {"phase": phase.value},
                "scores": {"quality": 0.8 + idx * 0.02},
                "confidence": confidences[idx],
                "metadata": {"contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.PASS.value,
            },
            scores={"quality": 0.8 + idx * 0.02},
            prompt_hash="hash",
            model_hash="model",
            phase=phase.value,
        )

        if phase == PipelinePhase.FINALIZE:
            entry.decision_artifact = DecisionArtifact(
                verdict=DecisionOutcome.PASS,
                justification="golden trace verification",
                supporting_trace_ids=[],
            )
            entry.epistemic_verdict = EpistemicVerdict.CERTAIN

        recorder.record_entry(entry)

    recorder.finish()

    assert trace_path.exists()
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    recorded_phases = [entry["phase"] for entry in data["entries"]]
    assert recorded_phases == [phase.value for phase in phases]

    decisions = {
        entry["output"]["decision"]
        for entry in data["entries"]
        if entry.get("output") and entry["output"]
    }
    assert decisions == {DecisionOutcome.PASS.value}

    confidence_values = [
        entry["output"]["confidence"]
        for entry in data["entries"]
        if entry.get("output") and "confidence" in entry["output"]
    ]
    assert confidence_values == sorted(confidence_values)

    signature = hashlib.sha256(
        "|".join(
            f"{entry['phase']}:{entry['output']['confidence']:.2f}:{entry['output']['decision']}"
            for entry in data["entries"]
            if entry.get("output")
        ).encode("utf-8")
    ).hexdigest()
    assert (
        signature == "b733534e1e10b134ae48a91b41e10bde6e545d3012eb0d6aa69d3ccf5a93fa64"
    )


def test_pipeline_failure_snapshot_matches_baseline() -> None:
    failure_fingerprint = build_run_fingerprint()
    entries = [
        TraceEntry(
            agent_id="PlannerAgent",
            node="planner",
            status="success",
            start_time=datetime(2024, 1, 5, tzinfo=UTC),
            end_time=datetime(2024, 1, 5, tzinfo=UTC),
            input={"phase": PipelinePhase.PLAN.value},
            output={
                "text": "plan",
                "artifacts": {"phase": PipelinePhase.PLAN.value},
                "scores": {"quality": 0.8},
                "confidence": 0.8,
                "metadata": {"contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.PASS.value,
            },
            scores={"quality": 0.8},
            prompt_hash="plan",
            model_hash="plan",
            phase=PipelinePhase.PLAN.value,
            run_id="failure-run",
            replay_metadata=build_replay_metadata(
                input_hash="plan-input",
                model_id="PlannerAgent",
            ),
            run_fingerprint=failure_fingerprint,
        ),
        TraceEntry(
            agent_id="SummarizerAgent",
            node="summarizer",
            status="failed",
            start_time=datetime(2024, 1, 5, tzinfo=UTC),
            end_time=datetime(2024, 1, 5, tzinfo=UTC),
            input={"phase": PipelinePhase.ABORTED.value},
            output={
                "text": "abort",
                "artifacts": {"phase": PipelinePhase.ABORTED.value},
                "scores": {"quality": 0.3},
                "confidence": 0.3,
                "metadata": {"contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.VETO.value,
            },
            scores={"quality": 0.3},
            prompt_hash="abort",
            model_hash="abort",
            phase=PipelinePhase.ABORTED.value,
            stop_reason=StopReason.USER_INTERRUPTION,
            failure_artifact=FailureArtifact(
                failure_class=FailureClass.USER_INTERRUPTION,
                mode="abort",
                message="simulated crash",
                phase=PipelinePhase.ABORTED,
                recoverable=False,
            ),
            epistemic_verdict=EpistemicVerdict.UNCERTAIN,
            run_id="failure-run",
            replay_metadata=build_replay_metadata(
                input_hash="abort-input",
                model_id="SummarizerAgent",
            ),
            run_fingerprint=failure_fingerprint,
        ),
    ]
    snapshot = {
        "trace": {
            "status": "aborted",
            "entries": [entry.to_dict() for entry in entries],
        },
        "outcome": {
            "status": "aborted",
            "decision": DecisionOutcome.VETO.value,
            "epistemic_verdict": EpistemicVerdict.UNCERTAIN.value,
            "confidence": 0.3,
        },
    }
    assert snapshot["trace"]["status"] == "aborted"
    assert snapshot["outcome"]["decision"] == DecisionOutcome.VETO.value
    failure_artifact = snapshot["trace"]["entries"][-1]["failure_artifact"]
    assert failure_artifact["failure_class"] == FailureClass.USER_INTERRUPTION.value
    assert failure_artifact["category"] == FailureCategory.OPERATIONAL.value


def test_trace_validation_detects_missing_entries() -> None:
    controller = PipelineController()
    entries: list[TraceEntry] = []
    for phase, agent_type in STANDARD_TRANSITIONS[:2]:
        controller.transition_to(phase)
        controller._align_agent(agent_type)
        entries.append(_build_entry(agent_type, phase))

    entries.clear()

    with pytest.raises(ValueError, match="Trace must contain at least one entry"):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_requires_stop_reason_for_abort() -> None:
    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(
            AgentType.PLANNER,
            PipelinePhase.ABORTED,
        ),
    ]

    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=StopReason.USER_INTERRUPTION,
            header=_test_header(),
        )

    entries[-1].stop_reason = StopReason.USER_INTERRUPTION

    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=StopReason.USER_INTERRUPTION,
            header=_test_header(),
        )

    entries[-1].failure_artifact = FailureArtifact(
        failure_class=FailureClass.USER_INTERRUPTION,
        mode="aborted",
        message="User interruption requested",
        phase=PipelinePhase.ABORTED,
        recoverable=False,
    )
    TraceValidator.validate(
        entries,
        CANONICAL_DEFINITION,
        stop_reason=StopReason.USER_INTERRUPTION,
        header=_test_header(),
    )


def test_trace_accepts_epistemic_failure_stop_reason() -> None:
    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(
            AgentType.PLANNER,
            PipelinePhase.ABORTED,
            stop_reason=StopReason.EPISTEMIC_FAILURE,
            failure_artifact=FailureArtifact(
                failure_class=FailureClass.EPISTEMIC_UNCERTAINTY,
                mode="uncertain",
                message="Inspector flagged epistemic uncertainty",
                phase=PipelinePhase.ABORTED,
                recoverable=False,
                category=FailureCategory.EPISTEMIC,
            ),
            epistemic_verdict=EpistemicVerdict.UNCERTAIN,
        ),
    ]

    TraceValidator.validate(
        entries,
        CANONICAL_DEFINITION,
        stop_reason=StopReason.EPISTEMIC_FAILURE,
        header=_test_header(),
    )


def test_failure_path_records_epistemic_and_user_abort(
    test_artifacts_dir: Path,
) -> None:
    controller = PipelineController()
    controller.transition_to(PipelinePhase.PLAN)
    controller.transition_to(PipelinePhase.EXECUTE)
    controller.request_stop(StopReason.EPISTEMIC_FAILURE, details="uncertain signals")
    controller.request_stop(
        StopReason.USER_INTERRUPTION, details="manual abort requested"
    )

    assert controller.phase == PipelinePhase.ABORTED
    assert controller.stop_reason == StopReason.USER_INTERRUPTION
    assert controller.final_epistemic_verdict == EpistemicVerdict.UNCERTAIN

    trace_path = test_artifacts_dir / "failure_trace.json"
    recorder = TraceRecorder(
        run_id="failure-run",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )
    now = datetime(2024, 1, 2, tzinfo=UTC)

    recorder.record_entry(
        TraceEntry(
            agent_id="PlannerAgent",
            node="planner",
            status="success",
            start_time=now,
            end_time=now,
            input={"phase": "PLAN"},
            output={
                "text": "plan generated",
                "artifacts": {"phase": PipelinePhase.PLAN.value},
                "scores": {"quality": 0.85},
                "confidence": 0.85,
                "metadata": {"contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.PASS.value,
            },
            scores={"quality": 0.85},
            prompt_hash="plan-hash",
            model_hash="plan-model",
            phase=PipelinePhase.PLAN.value,
        )
    )
    recorder.record_entry(
        TraceEntry(
            agent_id="Controller",
            node="controller",
            status="failed",
            start_time=now,
            end_time=now,
            input={"phase": PipelinePhase.ABORTED.value},
            output={
                "text": "abort recorded",
                "artifacts": {"phase": PipelinePhase.ABORTED.value},
                "scores": {"quality": 0.4},
                "confidence": 0.4,
                "metadata": {"contract_version": CONTRACT_VERSION},
                "decision": DecisionOutcome.VETO.value,
            },
            scores={"quality": 0.4},
            prompt_hash="abort-hash",
            model_hash="abort-model",
            phase=PipelinePhase.ABORTED.value,
            stop_reason=StopReason.USER_INTERRUPTION,
            failure_artifact=FailureArtifact(
                failure_class=FailureClass.EPISTEMIC_UNCERTAINTY,
                mode="uncertain",
                message="epistemic failure triggered abort",
                phase=PipelinePhase.ABORTED,
                recoverable=False,
                category=FailureCategory.EPISTEMIC,
            ),
            epistemic_verdict=EpistemicVerdict.UNCERTAIN,
            run_fingerprint=_build_run_fingerprint(),
        )
    )
    recorder.finish(status="aborted")

    assert trace_path.exists()
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert data["status"] == "aborted"
    final_entry = data["entries"][-1]
    assert final_entry["stop_reason"] == StopReason.USER_INTERRUPTION.value
    assert final_entry["failure_artifact"] is not None
    assert (
        final_entry["failure_artifact"]["category"] == FailureCategory.EPISTEMIC.value
    )

    TraceValidator.validate(
        list(recorder.trace.entries),
        CANONICAL_DEFINITION,
        stop_reason=StopReason.USER_INTERRUPTION,
        header=_test_header(),
    )


def test_pipeline_aborts_on_confidence_threshold() -> None:
    controller = PipelineController()
    controller.transition_to(PipelinePhase.PLAN)
    controller.transition_to(PipelinePhase.EXECUTE)

    controller.request_stop(
        StopReason.CONFIDENCE_THRESHOLD_MET,
        details="quality guard triggered",
    )

    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN, run_id="abort-run"),
        _build_entry(
            AgentType.SUMMARIZER,
            PipelinePhase.ABORTED,
            run_id="abort-run",
            stop_reason=StopReason.CONFIDENCE_THRESHOLD_MET,
            epistemic_verdict=EpistemicVerdict.UNCERTAIN,
        ),
    ]
    trace = _trace_from_entries("abort-run", entries, status="aborted")
    outcome = controller.finalize(trace)
    assert outcome.status == PipelineStatus.ABORTED
    assert controller.phase == PipelinePhase.ABORTED
    assert controller.stop_reason == StopReason.CONFIDENCE_THRESHOLD_MET
    assert outcome.epistemic_verdict != EpistemicVerdict.CERTAIN
    assert controller.final_epistemic_verdict == EpistemicVerdict.UNCERTAIN


def test_trace_meta_enforces_contractual_fields(test_artifacts_dir: Path) -> None:
    trace_path = test_artifacts_dir / "meta_consistency.json"
    recorder = TraceRecorder(
        run_id="meta-run",
        path=trace_path,
        model_metadata=default_model_metadata(),
    )
    now = datetime(2024, 1, 3, tzinfo=UTC)
    entry = TraceEntry(
        agent_id="MetaAgent",
        node="meta",
        status="success",
        start_time=now,
        end_time=now,
        input={"phase": PipelinePhase.PLAN.value},
        output={
            "text": "meta trace entry",
            "artifacts": {"phase": PipelinePhase.PLAN.value},
            "scores": {"quality": 0.7},
            "confidence": 0.7,
            "metadata": {"contract_version": CONTRACT_VERSION},
            "decision": DecisionOutcome.PASS.value,
        },
        scores={"quality": 0.7},
        prompt_hash="meta-snapshot",
        model_hash="meta-model",
    )
    recorder.record_entry(entry)
    recorder.finish()

    project_root = Path(__file__).resolve().parents[2]
    artifacts_root = project_root / "artifacts" / "test"
    assert trace_path.resolve().is_relative_to(artifacts_root)

    data = json.loads(trace_path.read_text(encoding="utf-8"))
    for item in data["entries"]:
        assert item.get("run_id"), "run_id is required on every trace entry"
        metadata = item.get("output", {}).get("metadata") or {}
        assert metadata.get("contract_version"), "contract_version must be recorded"
        assert "confidence" in (item.get("output") or {}), "confidence must be reported"


def test_epistemic_failure_requires_non_certain_verdict() -> None:
    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(
            AgentType.PLANNER,
            PipelinePhase.ABORTED,
            stop_reason=StopReason.EPISTEMIC_FAILURE,
            failure_artifact=FailureArtifact(
                failure_class=FailureClass.EPISTEMIC_UNCERTAINTY,
                mode="uncertain",
                message="Inspector flagged epistemic uncertainty",
                phase=PipelinePhase.ABORTED,
                recoverable=False,
                category=FailureCategory.EPISTEMIC,
            ),
            epistemic_verdict=EpistemicVerdict.CERTAIN,
        ),
    ]

    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=StopReason.EPISTEMIC_FAILURE,
            header=_test_header(),
        )


def test_trace_validator_rejects_out_of_order_phases() -> None:
    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(AgentType.SUMMARIZER, PipelinePhase.EXECUTE),
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
    ]

    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_requires_decision_artifact_for_final_entry() -> None:
    fingerprint = _build_run_fingerprint()
    entries = _build_standard_entries("no-artifact", fingerprint)
    entries[-1] = _build_entry(
        AgentType.ORCHESTRATOR,
        PipelinePhase.FINALIZE,
        run_id="no-artifact",
        run_fingerprint=fingerprint,
        attach_decision_artifact=False,
    )
    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_completeness_requires_each_phase() -> None:
    completeness_definition = PipelineDefinition(
        name="completeness",
        phases=list(PHASE_SEQUENCE),
        terminal_phases={PipelinePhase.DONE},
        allowed_transitions={
            PipelinePhase.INIT: {PipelinePhase.PLAN},
            PipelinePhase.PLAN: {PipelinePhase.EXECUTE},
            PipelinePhase.EXECUTE: {PipelinePhase.JUDGE},
            PipelinePhase.JUDGE: {PipelinePhase.VERIFY, PipelinePhase.FINALIZE},
            PipelinePhase.VERIFY: {PipelinePhase.FINALIZE},
            PipelinePhase.FINALIZE: {PipelinePhase.DONE},
        },
        skip_reasons={
            PipelinePhase.INIT: "Initialization is implicit",
            PipelinePhase.DONE: "Finality implied",
        },
    )

    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(AgentType.SUMMARIZER, PipelinePhase.EXECUTE),
        _build_entry(AgentType.JUDGE, PipelinePhase.JUDGE),
        _build_entry(AgentType.ORCHESTRATOR, PipelinePhase.FINALIZE),
    ]

    with pytest.raises(RuntimeError):
        TraceValidator.validate(
            entries,
            completeness_definition,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_completeness_allows_skipped_phase_with_reason() -> None:
    skipping_definition = PipelineDefinition(
        name="skip-verify",
        phases=list(PHASE_SEQUENCE),
        terminal_phases={PipelinePhase.DONE},
        allowed_transitions={
            PipelinePhase.INIT: {PipelinePhase.PLAN},
            PipelinePhase.PLAN: {PipelinePhase.EXECUTE},
            PipelinePhase.EXECUTE: {PipelinePhase.JUDGE},
            PipelinePhase.JUDGE: {PipelinePhase.FINALIZE},
            PipelinePhase.FINALIZE: {PipelinePhase.DONE},
        },
        skip_reasons={
            PipelinePhase.INIT: "Implicit start",
            PipelinePhase.VERIFY: "Verification intentionally skipped",
            PipelinePhase.DONE: "Terminal",
        },
    )
    fingerprint = RunFingerprint.create(
        definition=skipping_definition,
        config={"mode": "test"},
    )

    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(AgentType.SUMMARIZER, PipelinePhase.EXECUTE),
        _build_entry(AgentType.JUDGE, PipelinePhase.JUDGE),
        _build_entry(
            AgentType.ORCHESTRATOR,
            PipelinePhase.FINALIZE,
            run_fingerprint=fingerprint,
        ),
    ]

    TraceValidator.validate(
        entries,
        skipping_definition,
        stop_reason=None,
        header=_test_header(),
    )


def test_trace_replay_equivalence_maintains_metadata() -> None:
    fingerprint = _build_run_fingerprint()
    stored_runs: list[list[TraceEntry]] = []
    convergence_hashes: list[str | None] = []

    for run_id in ("run-a", "run-b"):
        entries = _build_standard_entries(run_id, fingerprint)
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )
        monitor = _standard_convergence_monitor()
        stored_runs.append(entries)
        convergence_hashes.append(monitor.trace_metadata[-1]["convergence_hash"])

    first, second = stored_runs
    assert [entry.phase for entry in first] == [entry.phase for entry in second]
    assert convergence_hashes[0] == convergence_hashes[1]
    assert first[-1].epistemic_verdict == second[-1].epistemic_verdict


def test_run_fingerprint_changes_on_contract_updates() -> None:
    base = _build_run_fingerprint()
    updated = _build_run_fingerprint(contract_version="0.2.0")
    assert base.fingerprint != updated.fingerprint


def test_interrupt_monitor_allows_manual_trigger() -> None:
    monitor = InterruptMonitor()
    assert not monitor.is_interrupted()
    monitor.trigger()
    assert monitor.is_interrupted()

    with monitor.watch() as active:
        active.trigger()
        assert active.is_interrupted()


def test_stop_request_transitions_to_aborted() -> None:
    controller = PipelineController()
    controller.request_stop(StopReason.MAX_ITERATIONS, details="test")
    assert controller.should_stop()
    assert controller.phase == PipelinePhase.ABORTED
    assert controller.stop_reason == StopReason.MAX_ITERATIONS


def test_trace_detects_adversarial_confidence_veto() -> None:
    fingerprint = _build_run_fingerprint()
    entries = _build_standard_entries("adversarial", fingerprint)
    final_entry = entries[-1]
    final_entry.output["confidence"] = 1.0
    final_entry.decision_artifact = DecisionArtifact(
        verdict=DecisionOutcome.VETO,
        justification="agent claims veto with certainty",
        supporting_trace_ids=[],
    )
    final_entry.epistemic_verdict = EpistemicVerdict.CERTAIN

    with pytest.raises(
        RuntimeError, match="Veto decisions must surface epistemic uncertainty"
    ):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_disallows_entries_after_abort() -> None:
    entries = [
        _build_entry(AgentType.PLANNER, PipelinePhase.PLAN),
        _build_entry(AgentType.SUMMARIZER, PipelinePhase.EXECUTE),
        _build_entry(
            AgentType.PLANNER,
            PipelinePhase.ABORTED,
            stop_reason=StopReason.USER_INTERRUPTION,
            failure_artifact=FailureArtifact(
                failure_class=FailureClass.USER_INTERRUPTION,
                mode="abort",
                message="mid-run failure",
                phase=PipelinePhase.ABORTED,
                recoverable=False,
            ),
            epistemic_verdict=EpistemicVerdict.UNCERTAIN,
        ),
        _build_entry(AgentType.JUDGE, PipelinePhase.JUDGE),
    ]

    with pytest.raises(
        RuntimeError, match="Trace may not continue after an aborted phase"
    ):
        TraceValidator.validate(
            entries,
            CANONICAL_DEFINITION,
            stop_reason=StopReason.USER_INTERRUPTION,
            header=_test_header(),
        )


def test_trace_rejects_missing_phase_information() -> None:
    entry = _build_entry(AgentType.PLANNER, PipelinePhase.PLAN)
    entry.phase = ""
    entry.input = {}
    with pytest.raises(RuntimeError, match="Trace entry missing phase information"):
        TraceValidator.validate(
            [entry],
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


def test_trace_rejects_unknown_phase() -> None:
    entry = _build_entry(AgentType.PLANNER, PipelinePhase.PLAN)
    entry.phase = "UNKNOWN"
    with pytest.raises(RuntimeError, match="Unknown phase recorded: UNKNOWN"):
        TraceValidator.validate(
            [entry],
            CANONICAL_DEFINITION,
            stop_reason=None,
            header=_test_header(),
        )


@pytest.mark.asyncio
async def test_pipeline_controller_handles_interrupt_race_condition() -> None:
    controller = PipelineController()
    controller.transition_to(PipelinePhase.PLAN)

    async def run_phase() -> None:
        controller.transition_to(PipelinePhase.EXECUTE)
        try:
            await asyncio.sleep(0.05)
            controller.transition_to(PipelinePhase.JUDGE)
        except RuntimeError:
            pass

    task = asyncio.create_task(run_phase())
    await asyncio.sleep(0.01)
    controller.request_stop(StopReason.USER_INTERRUPTION, details="manual stop")
    await task

    aborted_entry = _build_entry(
        AgentType.SUMMARIZER,
        PipelinePhase.ABORTED,
        run_id="interrupt-run",
        stop_reason=StopReason.USER_INTERRUPTION,
        epistemic_verdict=EpistemicVerdict.UNCERTAIN,
    )
    trace = _trace_from_entries("interrupt-run", [aborted_entry], status="aborted")
    outcome = controller.finalize(trace)
    assert outcome.status == PipelineStatus.ABORTED
    assert controller.stop_reason == StopReason.USER_INTERRUPTION
    assert controller.phase == PipelinePhase.ABORTED
