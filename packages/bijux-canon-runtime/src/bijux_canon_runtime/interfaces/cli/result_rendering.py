# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Result rendering helpers for the runtime CLI."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any

from bijux_canon_runtime.observability.analysis.trace_diff import entropy_summary
from bijux_canon_runtime.observability.classification.determinism_classification import (
    determinism_classes_for_trace,
    determinism_profile_for_trace,
)
from bijux_canon_runtime.ontology.public import ReplayAcceptability


def render_result(command: str, result: Any, *, json_output: bool) -> None:
    """Render a CLI command result."""
    if json_output:
        render_json_result(command, result)
        return
    render_human_result(command, result)


def render_json_result(command: str, result: Any) -> None:
    """Render a runtime result as stable JSON."""
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
                "status": verification.status,
                "rule_ids": verification.violations,
                "escalated": verification.status == "ESCALATE",
            }
            for index, verification in enumerate(result.verification_results)
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
            "replay_confidence": replay_confidence(
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


def render_human_result(command: str, result: Any) -> None:
    """Render a runtime result as human-readable text."""
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


def replay_confidence(acceptability: ReplayAcceptability) -> str:
    """Map replay acceptability to the CLI confidence label."""
    if acceptability == ReplayAcceptability.EXACT_MATCH:
        return "exact"
    if acceptability == ReplayAcceptability.INVARIANT_PRESERVING:
        return "invariant_preserving"
    if acceptability == ReplayAcceptability.STATISTICALLY_BOUNDED:
        return "statistically_bounded"
    raise AssertionError(f"unsupported replay acceptability: {acceptability!r}")


__all__ = [
    "render_human_result",
    "render_json_result",
    "render_result",
    "replay_confidence",
]
