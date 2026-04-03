# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for cli/main.py."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

from agentic_flows.core.errors import ConfigurationError, classify_failure
from agentic_flows.runtime.observability.analysis.trace_diff import (
    entropy_summary,
    semantic_trace_diff,
)
from agentic_flows.runtime.observability.classification.determinism_classification import (
    determinism_classes_for_trace,
    determinism_profile_for_trace,
)
from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.runtime.orchestration.planner import ExecutionPlanner
from agentic_flows.runtime.orchestration.replay_store import replay_with_store
from agentic_flows.spec.model.artifact.entropy_budget import (
    EntropyBudget,
    EntropyBudgetSlice,
)
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.verification.arbitration_policy import ArbitrationPolicy
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_rule import VerificationRule
from agentic_flows.spec.ontology import (
    ArbitrationRule,
    DatasetState,
    DeterminismLevel,
    EntropyExhaustionAction,
    EntropyMagnitude,
    FlowState,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    EvidenceID,
    FlowID,
    GateID,
    RuleID,
    RunID,
    TenantID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    NonDeterminismIntentSource,
    ReplayAcceptability,
    ReplayMode,
)


def _load_manifest(path: Path) -> FlowManifest:
    """Internal helper; not part of the public API."""
    raw_contents = path.read_text(encoding="utf-8")
    payload = json.loads(raw_contents)
    allowed_keys = {
        "flow_id",
        "tenant_id",
        "flow_state",
        "determinism_level",
        "replay_mode",
        "replay_acceptability",
        "entropy_budget",
        "allowed_variance_class",
        "nondeterminism_intent",
        "replay_envelope",
        "dataset",
        "allow_deprecated_datasets",
        "agents",
        "dependencies",
        "retrieval_contracts",
        "verification_gates",
    }
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        raise ConfigurationError(",".join(unknown_keys))
    determinism_value = payload.get("determinism_level")
    if determinism_value in (None, "", "default"):
        raise ConfigurationError("determinism_level")
    return FlowManifest(
        spec_version="v1",
        flow_id=FlowID(payload["flow_id"]),
        tenant_id=TenantID(payload["tenant_id"]),
        flow_state=FlowState(payload["flow_state"]),
        determinism_level=DeterminismLevel(payload["determinism_level"]),
        replay_mode=ReplayMode(payload.get("replay_mode", "strict")),
        replay_acceptability=ReplayAcceptability(payload["replay_acceptability"]),
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=tuple(
                EntropySource(source)
                for source in payload["entropy_budget"]["allowed_sources"]
            ),
            max_magnitude=EntropyMagnitude(payload["entropy_budget"]["max_magnitude"]),
            min_magnitude=EntropyMagnitude(
                payload["entropy_budget"].get("min_magnitude", "low")
            ),
            exhaustion_action=EntropyExhaustionAction(
                payload["entropy_budget"].get("exhaustion_action", "halt")
            ),
            per_source=tuple(
                EntropyBudgetSlice(
                    source=EntropySource(entry["source"]),
                    min_magnitude=EntropyMagnitude(entry["min_magnitude"]),
                    max_magnitude=EntropyMagnitude(entry["max_magnitude"]),
                    exhaustion_action=EntropyExhaustionAction(
                        entry["exhaustion_action"]
                    )
                    if entry.get("exhaustion_action") is not None
                    else None,
                )
                for entry in payload["entropy_budget"].get("per_source", [])
            ),
        ),
        allowed_variance_class=EntropyMagnitude(payload["allowed_variance_class"])
        if payload.get("allowed_variance_class") is not None
        else None,
        nondeterminism_intent=tuple(
            NonDeterministicIntent(
                spec_version="v1",
                source=NonDeterminismIntentSource(entry["source"]),
                min_entropy_magnitude=EntropyMagnitude(entry["min_entropy_magnitude"]),
                max_entropy_magnitude=EntropyMagnitude(entry["max_entropy_magnitude"]),
                justification=entry["justification"],
            )
            for entry in payload.get("nondeterminism_intent", [])
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=float(payload["replay_envelope"]["min_claim_overlap"]),
            max_contradiction_delta=int(
                payload["replay_envelope"]["max_contradiction_delta"]
            ),
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID(payload["dataset"]["dataset_id"]),
            tenant_id=TenantID(payload["dataset"]["tenant_id"]),
            dataset_version=payload["dataset"]["dataset_version"],
            dataset_hash=payload["dataset"]["dataset_hash"],
            dataset_state=DatasetState(payload["dataset"]["dataset_state"]),
            storage_uri=payload["dataset"]["storage_uri"],
        ),
        allow_deprecated_datasets=bool(payload["allow_deprecated_datasets"]),
        agents=tuple(AgentID(agent_id) for agent_id in payload["agents"]),
        dependencies=tuple(payload["dependencies"]),
        retrieval_contracts=tuple(
            ContractID(contract) for contract in payload["retrieval_contracts"]
        ),
        verification_gates=tuple(
            GateID(gate) for gate in payload["verification_gates"]
        ),
    )


def _load_policy(path: Path) -> VerificationPolicy:
    """Internal helper; not part of the public API."""
    raw_contents = path.read_text(encoding="utf-8")
    payload = json.loads(raw_contents)
    arbitration = payload["arbitration_policy"]
    rules = tuple(
        VerificationRule(
            spec_version=rule["spec_version"],
            rule_id=RuleID(rule["rule_id"]),
            description=rule["description"],
            severity=rule["severity"],
            target=rule["target"],
            randomness_requirement=VerificationRandomness(
                rule["randomness_requirement"]
            ),
            cost=int(rule["cost"]),
        )
        for rule in payload["rules"]
    )
    return VerificationPolicy(
        spec_version=payload["spec_version"],
        verification_level=payload["verification_level"],
        failure_mode=payload["failure_mode"],
        randomness_tolerance=VerificationRandomness(payload["randomness_tolerance"]),
        arbitration_policy=ArbitrationPolicy(
            spec_version=arbitration["spec_version"],
            rule=ArbitrationRule(arbitration["rule"]),
            quorum_threshold=arbitration["quorum_threshold"],
        ),
        required_evidence=tuple(
            EvidenceID(value) for value in payload["required_evidence"]
        ),
        max_rule_cost=int(payload["max_rule_cost"]),
        rules=rules,
        fail_on=tuple(RuleID(value) for value in payload["fail_on"]),
        escalate_on=tuple(RuleID(value) for value in payload["escalate_on"]),
    )


# Stable commands: run, replay, inspect.
# Diagnostic-only commands: experimental/* (plan, dry-run, unsafe-run, diff, explain, validate).
# The CLI is not the primary API surface; contract-first integration should use the API schema.
EXIT_FAILURE = 1
EXIT_CONTRACT_VIOLATION = 2


def main() -> None:
    """Execute main and enforce its contract."""
    parser = argparse.ArgumentParser(
        prog="agentic-flows",
        description=(
            "All completed runs are expected to be replayable unless explicitly "
            "documented otherwise."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help=(
            "Deterministic when strict mode and declared contracts are satisfied; "
            "output stability is guaranteed only within v1."
        ),
    )
    run_parser.add_argument("manifest")
    run_parser.add_argument("--policy", required=True)
    run_parser.add_argument("--db-path", required=True)
    run_parser.add_argument("--strict-determinism", action="store_true")
    run_parser.add_argument("--json", action="store_true")

    replay_parser = subparsers.add_parser(
        "replay",
        help=(
            "Replays enforce declared determinism thresholds; "
            "output stability is guaranteed only within v1."
        ),
    )
    replay_parser.add_argument("manifest")
    replay_parser.add_argument("--policy", required=True)
    replay_parser.add_argument("--run-id", required=True)
    replay_parser.add_argument("--tenant-id", required=True)
    replay_parser.add_argument("--db-path", required=True)
    replay_parser.add_argument("--strict-determinism", action="store_true")
    replay_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser(
        "inspect",
        help=(
            "Inspection reflects persisted state deterministically; "
            "output stability is guaranteed only within v1."
        ),
    )
    inspect_subparsers = inspect_parser.add_subparsers(dest="inspect_command")
    inspect_run_parser = inspect_subparsers.add_parser(
        "run",
        help=argparse.SUPPRESS,
    )
    inspect_run_parser.add_argument("run_id")
    inspect_run_parser.add_argument("--tenant-id", required=True)
    inspect_run_parser.add_argument("--db-path", required=True)
    inspect_run_parser.add_argument("--json", action="store_true")

    experimental_parser = subparsers.add_parser(
        "experimental",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    experimental_subparsers = experimental_parser.add_subparsers(
        dest="experimental_command"
    )

    plan_parser = experimental_subparsers.add_parser(
        "plan",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    plan_parser.add_argument("manifest")
    plan_parser.add_argument("--db-path")
    plan_parser.add_argument("--json", action="store_true")

    dry_run_parser = experimental_subparsers.add_parser(
        "dry-run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    dry_run_parser.add_argument("manifest")
    dry_run_parser.add_argument("--db-path", required=True)
    dry_run_parser.add_argument("--strict-determinism", action="store_true")
    dry_run_parser.add_argument("--json", action="store_true")

    unsafe_parser = experimental_subparsers.add_parser(
        "unsafe-run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    unsafe_parser.add_argument("manifest")
    unsafe_parser.add_argument("--db-path", required=True)
    unsafe_parser.add_argument("--strict-determinism", action="store_true")
    unsafe_parser.add_argument("--json", action="store_true")

    diff_parser = experimental_subparsers.add_parser(
        "diff",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    diff_subparsers = diff_parser.add_subparsers(dest="diff_command")
    diff_run_parser = diff_subparsers.add_parser(
        "run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    diff_run_parser.add_argument("run_a")
    diff_run_parser.add_argument("run_b")
    diff_run_parser.add_argument("--tenant-id", required=True)
    diff_run_parser.add_argument("--db-path", required=True)
    diff_run_parser.add_argument("--json", action="store_true")

    explain_parser = experimental_subparsers.add_parser(
        "explain",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    explain_subparsers = explain_parser.add_subparsers(dest="explain_command")
    explain_failure_parser = explain_subparsers.add_parser(
        "failure",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    explain_failure_parser.add_argument("run_id")
    explain_failure_parser.add_argument("--tenant-id", required=True)
    explain_failure_parser.add_argument("--db-path", required=True)
    explain_failure_parser.add_argument("--json", action="store_true")

    validate_parser = experimental_subparsers.add_parser(
        "validate",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    validate_db_parser = validate_subparsers.add_parser(
        "db",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    validate_db_parser.add_argument("--db-path", required=True)
    validate_db_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "inspect" and args.inspect_command == "run":
        _inspect_run(args, json_output=args.json)
        return
    if args.command == "replay":
        _replay_run(args, json_output=args.json)
        return
    if (
        args.command == "experimental"
        and args.experimental_command == "diff"
        and args.diff_command == "run"
    ):
        _diff_runs(args, json_output=args.json)
        return
    if (
        args.command == "experimental"
        and args.experimental_command == "explain"
        and args.explain_command == "failure"
    ):
        _explain_failure(args, json_output=args.json)
        return
    if (
        args.command == "experimental"
        and args.experimental_command == "validate"
        and args.validate_command == "db"
    ):
        _validate_db(args, json_output=args.json)
        return

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)

    command = args.command
    if args.command == "experimental":
        command = args.experimental_command

    config = ExecutionConfig.from_command(command)
    config = replace(config, determinism_level=manifest.determinism_level)
    if getattr(args, "db_path", None):
        config = ExecutionConfig(
            mode=config.mode,
            determinism_level=manifest.determinism_level,
            execution_store=DuckDBExecutionWriteStore(Path(args.db_path)),
        )
    if getattr(args, "strict_determinism", False):
        config = replace(config, strict_determinism=True)
    if getattr(args, "policy", None):
        policy = _load_policy(Path(args.policy))
        config = replace(config, verification_policy=policy)
    try:
        result = execute_flow(manifest, config=config)
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            print(str(exc), file=sys.stderr)
            raise SystemExit(EXIT_CONTRACT_VIOLATION) from exc
        try:
            failure_class = classify_failure(exc)
        except KeyError:
            raise
        print(f"Failure: {failure_class.value}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE) from exc
    _render_result(command, result, json_output=args.json)


def _render_result(command: str, result, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    if json_output:
        _render_json_result(command, result)
        return
    _render_human_result(command, result)


def _render_json_result(command: str, result) -> None:
    """Internal helper; not part of the public API."""
    if command == "plan":
        payload = asdict(result.resolved_flow.plan)
        print(json.dumps(payload, sort_keys=True))
        return
    if command == "dry-run":
        payload = asdict(result.trace)
        print(json.dumps(payload, sort_keys=True))
        return
    if command in {"run", "unsafe-run"}:
        payload = asdict(result.trace)
        artifact_list = [
            {"artifact_id": artifact.artifact_id, "content_hash": artifact.content_hash}
            for artifact in result.artifacts
        ]
        retrieval_requests = [
            {
                "request_id": step.retrieval_request.request_id,
                "vector_contract_id": step.retrieval_request.vector_contract_id,
            }
            for step in result.resolved_flow.plan.steps
            if step.retrieval_request is not None
        ]
        evidence_list = [
            {
                "evidence_id": item.evidence_id,
                "content_hash": item.content_hash,
                "vector_contract_id": item.vector_contract_id,
                "determinism": item.determinism,
            }
            for item in result.evidence
        ]
        claims_list = [
            {
                "claim_id": claim.claim_id,
                "confidence": claim.confidence,
                "evidence_ids": claim.supported_by,
            }
            for bundle in result.reasoning_bundles
            for claim in bundle.claims
        ]
        verification_list = [
            {
                "step_index": result.resolved_flow.plan.steps[index].step_index,
                "status": result.status,
                "rule_ids": result.violations,
                "escalated": result.status == "ESCALATE",
            }
            for index, result in enumerate(result.verification_results)
        ]
        output = {
            "trace": payload,
            "determinism_level": result.resolved_flow.plan.determinism_level,
            "replay_acceptability": result.resolved_flow.plan.replay_acceptability,
            "determinism_profile": (
                asdict(determinism_profile_for_trace(result.trace))
                if result.trace is not None
                else None
            ),
            "dataset": {
                "dataset_id": result.resolved_flow.plan.dataset.dataset_id,
                "tenant_id": result.resolved_flow.plan.dataset.tenant_id,
                "dataset_version": result.resolved_flow.plan.dataset.dataset_version,
                "dataset_hash": result.resolved_flow.plan.dataset.dataset_hash,
                "dataset_state": result.resolved_flow.plan.dataset.dataset_state,
            },
            "non_determinism_summary": entropy_summary(result.trace.entropy_usage),
            "entropy_used": [
                {
                    "source": usage.source,
                    "magnitude": usage.magnitude,
                    "description": usage.description,
                    "step_index": usage.step_index,
                }
                for usage in result.trace.entropy_usage
            ]
            if result.trace is not None
            else [],
            "replay_confidence": _replay_confidence(
                result.resolved_flow.plan.replay_acceptability
            ),
            "artifact": artifact_list,
            "retrieval_requests": retrieval_requests,
            "retrieval_evidence": evidence_list,
            "reasoning_claims": claims_list,
            "verification": verification_list,
        }
        print(json.dumps(output, sort_keys=True))
        return
    print(json.dumps({"flow_id": result.resolved_flow.manifest.flow_id}))


def _render_human_result(command: str, result) -> None:
    """Internal helper; not part of the public API."""
    if command == "plan":
        plan = result.resolved_flow.plan
        print(
            f"Plan ready: flow_id={plan.flow_id} steps={len(plan.steps)} "
            f"dataset={plan.dataset.dataset_id}"
        )
        return
    if command == "dry-run":
        trace = result.trace
        print(
            f"Dry-run trace: run_id={result.run_id} events={len(trace.events)} "
            f"artifact={len(result.artifacts)}"
        )
        determinism_class = determinism_classes_for_trace(trace) if trace else []
        summary = ", ".join(determinism_class) if determinism_class else "unknown"
        print(f"Determinism class: {summary}")
        if trace is not None:
            profile = determinism_profile_for_trace(trace)
            print(
                "Determinism profile: "
                f"magnitude={profile.entropy_magnitude} "
                f"sources={','.join(source.value for source in profile.entropy_sources)} "
                f"decay={profile.confidence_decay:.2f}"
            )
        return
    if command in {"run", "unsafe-run"}:
        trace = result.trace
        entropy_count = len(trace.entropy_usage) if trace is not None else 0
        print(
            f"Run complete: run_id={result.run_id} steps={len(result.resolved_flow.plan.steps)} "
            f"artifact={len(result.artifacts)} evidence={len(result.evidence)} "
            f"entropy_entries={entropy_count}"
        )
        determinism_class = determinism_classes_for_trace(trace) if trace else []
        summary = ", ".join(determinism_class) if determinism_class else "unknown"
        print(f"Determinism class: {summary}")
        if trace is not None:
            profile = determinism_profile_for_trace(trace)
            print(
                "Determinism profile: "
                f"magnitude={profile.entropy_magnitude} "
                f"sources={','.join(source.value for source in profile.entropy_sources)} "
                f"decay={profile.confidence_decay:.2f}"
            )
        return
    print(f"Flow loaded: {result.resolved_flow.manifest.flow_id}")


def _normalize_for_json(value, *, normalize_timestamps: bool = False):
    """Internal helper; not part of the public API."""
    if isinstance(value, tuple):
        return [
            _normalize_for_json(item, normalize_timestamps=normalize_timestamps)
            for item in value
        ]
    if isinstance(value, list):
        normalized = [
            _normalize_for_json(item, normalize_timestamps=normalize_timestamps)
            for item in value
        ]
        if normalize_timestamps and all(isinstance(item, str) for item in normalized):
            return sorted(normalized)
        return normalized
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if normalize_timestamps and "timestamp" in key:
                normalized[key] = "normalized"
            else:
                normalized[key] = _normalize_for_json(
                    item, normalize_timestamps=normalize_timestamps
                )
        return normalized
    if hasattr(value, "value"):
        return value.value
    return value


def _inspect_run(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    trace = store.load_trace(RunID(args.run_id), tenant_id=TenantID(args.tenant_id))
    if json_output:
        payload = _normalize_for_json(asdict(trace))
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        f"Run {args.run_id}: events={len(trace.events)} "
        f"tool_invocations={len(trace.tool_invocations)} "
        f"entropy_entries={len(trace.entropy_usage)}"
    )


def _diff_runs(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    tenant_id = TenantID(args.tenant_id)
    trace_a = store.load_trace(RunID(args.run_a), tenant_id=tenant_id)
    trace_b = store.load_trace(RunID(args.run_b), tenant_id=tenant_id)
    diff = semantic_trace_diff(
        trace_a, trace_b, acceptability=trace_a.replay_acceptability
    )
    if json_output:
        print(json.dumps(_normalize_for_json(diff), sort_keys=True))
        return
    if diff:
        print(f"Diff detected: keys={', '.join(sorted(diff.keys()))}")
    else:
        print("Diff clean: no semantic differences")


def _explain_failure(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    trace = store.load_trace(RunID(args.run_id), tenant_id=TenantID(args.tenant_id))
    failure_events = [
        event
        for event in trace.events
        if event.event_type.value
        in {
            "STEP_FAILED",
            "RETRIEVAL_FAILED",
            "REASONING_FAILED",
            "VERIFICATION_FAIL",
            "TOOL_CALL_FAIL",
            "EXECUTION_INTERRUPTED",
        }
    ]
    payload = {
        "run_id": args.run_id,
        "failure": _normalize_for_json(
            failure_events[-1].payload, normalize_timestamps=True
        )
        if failure_events
        else None,
        "event_type": failure_events[-1].event_type.value if failure_events else None,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    if failure_events:
        last = failure_events[-1]
        print(f"Failure {last.event_type.value}: {_normalize_for_json(last.payload)}")
    else:
        print("No failure events recorded")


def _validate_db(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    DuckDBExecutionReadStore(Path(args.db_path))
    if json_output:
        print(json.dumps({"status": "ok"}, sort_keys=True))
        return
    print("DB validated: ok")


def _replay_confidence(acceptability: ReplayAcceptability) -> str:
    """Internal helper; not part of the public API."""
    if acceptability == ReplayAcceptability.EXACT_MATCH:
        return "exact"
    if acceptability == ReplayAcceptability.INVARIANT_PRESERVING:
        return "invariant_preserving"
    if acceptability == ReplayAcceptability.STATISTICALLY_BOUNDED:
        return "statistically_bounded"
    return "unknown"


def _replay_run(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    manifest = _load_manifest(Path(args.manifest))
    policy = _load_policy(Path(args.policy))
    planner = ExecutionPlanner()
    resolved_flow = planner.resolve(manifest)
    read_store = DuckDBExecutionReadStore(Path(args.db_path))
    write_store = DuckDBExecutionWriteStore(Path(args.db_path))
    config = ExecutionConfig(
        mode=_config_mode_for_replay(),
        determinism_level=manifest.determinism_level,
        execution_store=write_store,
        execution_read_store=read_store,
        verification_policy=policy,
        strict_determinism=bool(args.strict_determinism),
    )
    diff, result = replay_with_store(
        store=read_store,
        run_id=RunID(args.run_id),
        tenant_id=TenantID(args.tenant_id),
        resolved_flow=resolved_flow,
        config=config,
    )
    if json_output:
        payload = {
            "diff": _normalize_for_json(diff, normalize_timestamps=True),
            "trace": _normalize_for_json(
                asdict(result.trace), normalize_timestamps=True
            ),
            "run_id": str(result.run_id),
        }
        print(json.dumps(payload, sort_keys=True))
        if diff:
            reason_code = next(iter(diff))
            print(reason_code, file=sys.stderr)
            raise SystemExit(EXIT_CONTRACT_VIOLATION)
        return
    if diff:
        reason_code = next(iter(diff))
        print(reason_code)
        raise SystemExit(EXIT_CONTRACT_VIOLATION)
    else:
        print(f"Replay clean: run_id={result.run_id}")


def _config_mode_for_replay() -> RunMode:
    """Internal helper; not part of the public API."""
    return RunMode.LIVE
