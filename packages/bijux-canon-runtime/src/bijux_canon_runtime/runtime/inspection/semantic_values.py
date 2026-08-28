# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Resolve research semantics to exact persisted artifact locations."""

from __future__ import annotations

from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.inspection.models import (
    InspectedArtifact,
    PersistedInspectionValue,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    required_dict,
    required_list,
    required_object,
    required_string,
)

_SEMANTIC_KEYS = {
    "hits": "hits",
    "hit": "hits",
    "claims": "claims",
    "claim": "claims",
    "citations": "citations",
    "citation": "citations",
    "tool_calls": "tool_calls",
    "tool_call": "tool_calls",
    "tool_invocations": "tool_calls",
    "provider_calls": "provider_calls",
    "provider_call": "provider_calls",
    "provider_invocations": "provider_calls",
    "checks": "checks",
    "check_results": "checks",
}


def extract_semantics(
    artifacts: tuple[InspectedArtifact, ...],
    output_steps: dict[ArtifactID, str],
) -> dict[str, tuple[PersistedInspectionValue, ...]]:
    """Extract typed semantic collections from step output JSON."""
    found: dict[str, list[PersistedInspectionValue]] = {
        name: [] for name in set(_SEMANTIC_KEYS.values())
    }
    for artifact in artifacts:
        if artifact.artifact_id not in output_steps or artifact.json_value is None:
            continue
        _walk_semantics(
            artifact.json_value,
            path="$",
            artifact_id=artifact.artifact_id,
            step_id=output_steps[artifact.artifact_id],
            found=found,
        )
    return {name: tuple(values) for name, values in found.items()}


def plan_values(
    *,
    manifest_artifact_id: ArtifactID,
    plan: dict[str, object],
    field_name: str,
) -> tuple[PersistedInspectionValue, ...]:
    """Resolve repeated per-step plan inputs to their manifest paths."""
    values: list[PersistedInspectionValue] = []
    for index, raw_step in enumerate(required_list(plan, "steps")):
        step = required_dict(raw_step, "plan step")
        inputs = required_object(step, "inputs")
        value = inputs.get(field_name)
        if value is None:
            continue
        values.append(
            PersistedInspectionValue(
                manifest_artifact_id,
                required_string(step, "step_id"),
                f"$.plan.steps[{index}].inputs.{field_name}",
                value,
            )
        )
    return tuple(values)


def _walk_semantics(
    value: object,
    *,
    path: str,
    artifact_id: ArtifactID,
    step_id: str,
    found: dict[str, list[PersistedInspectionValue]],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            category = _SEMANTIC_KEYS.get(str(key).lower().replace("-", "_"))
            if category is not None:
                values = item if isinstance(item, list) else [item]
                found[category].extend(
                    PersistedInspectionValue(
                        artifact_id,
                        step_id,
                        (
                            f"{child_path}[{index}]"
                            if isinstance(item, list)
                            else child_path
                        ),
                        entry,
                    )
                    for index, entry in enumerate(values)
                )
            _walk_semantics(
                item,
                path=child_path,
                artifact_id=artifact_id,
                step_id=step_id,
                found=found,
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_semantics(
                item,
                path=f"{path}[{index}]",
                artifact_id=artifact_id,
                step_id=step_id,
                found=found,
            )


__all__ = ["extract_semantics", "plan_values"]
