# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Manifest loading helpers for the runtime CLI."""

from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.model.artifact.entropy_budget import (
    EntropyBudget,
    EntropyBudgetSlice,
)
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyExhaustionAction,
    EntropyMagnitude,
    FlowState,
)
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    FlowID,
    GateID,
    TenantID,
)
from bijux_canon_runtime.ontology.public import (
    EntropySource,
    NonDeterminismIntentSource,
    ReplayAcceptability,
    ReplayMode,
)


def load_manifest(path: Path) -> FlowManifest:
    """Load a runtime flow manifest from a JSON file."""
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


__all__ = ["load_manifest"]
