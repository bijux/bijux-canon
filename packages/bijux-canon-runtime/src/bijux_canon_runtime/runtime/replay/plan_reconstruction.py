# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Reconstruct typed replay plans from immutable execution manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    ConcreteStepInputs,
    DagOperation,
    ExecutionProfile,
    RetrievalFilters,
    RuntimeOutputPolicy,
    RuntimeRequestBudget,
    RuntimeRequestOperation,
    RuntimeRequestPlan,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.inspection import (
    RuntimeInspectionError,
    RuntimeRunInspection,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    optional_string,
    required_dict,
    required_list,
    required_object,
    required_string,
    required_strings,
)
from bijux_canon_runtime.runtime.replay.models import RuntimeReplayPolicy


@dataclass(frozen=True, slots=True)
class ReconstructedReplayPlan:
    """Typed plan and the source request identity it was derived from."""

    plan: RuntimeRequestPlan
    source_request_sha256: str


def reconstruct_replay_plan(
    inspection: RuntimeRunInspection,
    *,
    request_id: RequestID,
    policy: RuntimeReplayPolicy,
) -> ReconstructedReplayPlan:
    """Rebuild the exact source DAG with replay-bound immutable inputs."""
    return reconstruct_linked_plan(
        inspection,
        request_id=request_id,
        replay_mode=policy.replay_mode,
        linkage_kind="replay",
        execution_policy={
            "network_policy": policy.network_policy.value,
            "provider_allowlist": list(policy.provider_allowlist),
            "tolerance": asdict(policy.tolerance),
        },
    )


def reconstruct_linked_plan(
    inspection: RuntimeRunInspection,
    *,
    request_id: RequestID,
    replay_mode: ReplayMode,
    linkage_kind: str,
    execution_policy: dict[str, object],
) -> ReconstructedReplayPlan:
    """Clone an inspected DAG for a linked replay or recovery attempt."""
    if linkage_kind not in {"replay", "recovery"}:
        raise ValueError("linked plan kind must be replay or recovery")
    manifest = _selected_manifest(inspection)
    source_plan = required_object(manifest, "plan")
    steps = tuple(
        _reconstruct_step(
            required_dict(item, "plan step"),
            request_id=request_id,
            source_attempt_id=inspection.selected_attempt_id,
            replay_mode=replay_mode,
            linkage_kind=linkage_kind,
        )
        for item in required_list(source_plan, "steps")
    )
    source_request_sha256 = required_string(source_plan, "request_sha256")
    request_payload = {
        "execution_policy": execution_policy,
        "linkage_kind": linkage_kind,
        "replay_mode": replay_mode.value,
        "request_id": str(request_id),
        "schema_version": f"bijux.runtime.{linkage_kind}-request.v1",
        "source_attempt_id": inspection.selected_attempt_id,
        "source_request_sha256": source_request_sha256,
    }
    request_sha256 = hashlib.sha256(canonical_json_bytes(request_payload)).hexdigest()
    plan_payload = {
        "entry_step_ids": list(inspection.entry_step_ids),
        "request_id": str(request_id),
        "request_operation": inspection.request_operation,
        "request_sha256": request_sha256,
        "schema_version": "bijux.runtime.request-plan.v2",
        "steps": [_step_record(step) for step in steps],
        "terminal_step_ids": list(inspection.terminal_step_ids),
    }
    plan_sha256 = hashlib.sha256(canonical_json_bytes(plan_payload)).hexdigest()
    return ReconstructedReplayPlan(
        RuntimeRequestPlan(
            schema_version="bijux.runtime.request-plan.v2",
            request_id=request_id,
            request_operation=RuntimeRequestOperation(inspection.request_operation),
            request_sha256=request_sha256,
            plan_sha256=plan_sha256,
            entry_step_ids=inspection.entry_step_ids,
            terminal_step_ids=inspection.terminal_step_ids,
            steps=steps,
        ),
        source_request_sha256,
    )


def _selected_manifest(inspection: RuntimeRunInspection) -> dict[str, object]:
    candidates: list[dict[str, object]] = []
    for artifact in inspection.artifacts:
        if (
            artifact.schema_id != "bijux.runtime.execution-manifest.v1"
            or artifact.json_value is None
        ):
            continue
        payload = required_dict(artifact.json_value, "execution manifest")
        attempt = required_object(payload, "attempt")
        if required_string(attempt, "attempt_id") == inspection.selected_attempt_id:
            candidates.append(payload)
    if len(candidates) != 1:
        raise RuntimeInspectionError("selected attempt manifest is unresolved")
    return candidates[0]


def _reconstruct_step(
    record: dict[str, object],
    *,
    request_id: RequestID,
    source_attempt_id: str,
    replay_mode: ReplayMode,
    linkage_kind: str,
) -> ConcreteDagStep:
    inputs = required_object(record, "inputs")
    budget_record = required_object(inputs, "budget")
    filters_record = inputs.get("filters")
    output_record = inputs.get("output_policy")
    return ConcreteDagStep(
        step_id=required_string(record, "step_id"),
        operation=DagOperation(required_string(record, "operation")),
        depends_on=required_strings(record, "depends_on"),
        input_artifact_contract_ids=required_strings(
            record, "input_artifact_contract_ids"
        ),
        output_artifact_contract_ids=required_strings(
            record, "output_artifact_contract_ids"
        ),
        inputs=ConcreteStepInputs(
            request_id=request_id,
            request_operation=RuntimeRequestOperation(
                required_string(inputs, "request_operation")
            ),
            execution_profile=ExecutionProfile(
                required_string(inputs, "execution_profile")
            ),
            budget=RuntimeRequestBudget(
                timeout_seconds=_number(budget_record, "timeout_seconds"),
                max_artifact_bytes=_integer(budget_record, "max_artifact_bytes"),
                max_steps=_optional_integer(budget_record, "max_steps"),
                max_provider_tokens=_optional_integer(
                    budget_record, "max_provider_tokens"
                ),
            ),
            replay_mode=replay_mode,
            scope=required_string(inputs, "scope"),
            query=optional_string(inputs, "query"),
            source_directory=optional_string(inputs, "source_directory"),
            corpus_id=_optional_artifact_id(inputs, "corpus_id"),
            index_id=_optional_artifact_id(inputs, "index_id"),
            filters=(
                None
                if filters_record is None
                else RetrievalFilters(
                    document_ids=required_strings(
                        required_dict(filters_record, "filters"), "document_ids"
                    ),
                    source_uris=required_strings(
                        required_dict(filters_record, "filters"), "source_uris"
                    ),
                )
            ),
            top_k=_optional_integer(inputs, "top_k"),
            provider=optional_string(inputs, "provider"),
            output_policy=(
                None
                if output_record is None
                else RuntimeOutputPolicy(
                    require_citations=_boolean(
                        required_dict(output_record, "output_policy"),
                        "require_citations",
                    ),
                    permit_insufficient_answer=_boolean(
                        required_dict(output_record, "output_policy"),
                        "permit_insufficient_answer",
                    ),
                    publish=_boolean(
                        required_dict(output_record, "output_policy"), "publish"
                    ),
                )
            ),
            replay_attempt_id=(source_attempt_id if linkage_kind == "replay" else None),
            source_attempt_id=source_attempt_id,
        ),
    )


def _step_record(step: ConcreteDagStep) -> dict[str, object]:
    return {
        "depends_on": list(step.depends_on),
        "input_artifact_contract_ids": list(step.input_artifact_contract_ids),
        "inputs": _json_value(asdict(step.inputs)),
        "operation": step.operation.value,
        "output_artifact_contract_ids": list(step.output_artifact_contract_ids),
        "step_id": step.step_id,
    }


def _optional_artifact_id(record: dict[str, object], key: str) -> ArtifactID | None:
    value = optional_string(record, key)
    return None if value is None else ArtifactID(value)


def _integer(record: dict[str, object], key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeInspectionError(f"{key} must be an integer")
    return value


def _optional_integer(record: dict[str, object], key: str) -> int | None:
    value = record.get(key)
    return None if value is None else _integer(record, key)


def _number(record: dict[str, object], key: str) -> float:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RuntimeInspectionError(f"{key} must be a number")
    return float(value)


def _boolean(record: dict[str, object], key: str) -> bool:
    value = record.get(key)
    if not isinstance(value, bool):
        raise RuntimeInspectionError(f"{key} must be a boolean")
    return value


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


__all__ = [
    "ReconstructedReplayPlan",
    "reconstruct_linked_plan",
    "reconstruct_replay_plan",
]
