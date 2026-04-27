from __future__ import annotations

from bijux_canon_runtime.application.flow_execution_models import ExecutionConfig
from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.ontology import DatasetState, DeterminismLevel, FlowState
from bijux_canon_runtime.ontology.ids import DatasetID, TenantID
from bijux_canon_runtime.ontology.public import EntropySource, ReplayAcceptability
from bijux_canon_runtime.runtime.context import RunMode as ContextRunMode
import pytest


@pytest.mark.parametrize(
    ("command", "mode"),
    [
        ("plan", RunMode.PLAN),
        ("dry-run", RunMode.DRY_RUN),
        ("run", RunMode.LIVE),
        ("observe", RunMode.OBSERVE),
        ("unsafe-run", RunMode.UNSAFE),
    ],
)
def test_execution_config_from_command_maps_command_to_run_mode(
    command: str, mode: RunMode
) -> None:
    config = ExecutionConfig.from_command(command)

    assert config.mode is mode
    assert config.determinism_level is DeterminismLevel.STRICT


def test_execution_config_from_command_rejects_unknown_command() -> None:
    with pytest.raises(ValueError, match="Unsupported command: unknown"):
        ExecutionConfig.from_command("unknown")


def test_runtime_context_reexports_canonical_run_mode() -> None:
    assert ContextRunMode is RunMode


def test_execution_config_for_manifest_uses_manifest_determinism_level() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id="flow-1",
        tenant_id=TenantID("tenant-1"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.BOUNDED,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG,),
            max_magnitude="low",
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-1"),
            tenant_id=TenantID("tenant-1"),
            dataset_version="1.0.0",
            dataset_hash="hash-1",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://dataset.json",
        ),
        allow_deprecated_datasets=False,
        agents=(),
        dependencies=(),
        retrieval_contracts=(),
        verification_gates=(),
    )

    config = ExecutionConfig.from_command("run").for_manifest(manifest)

    assert config.mode is RunMode.LIVE
    assert config.determinism_level is DeterminismLevel.BOUNDED
