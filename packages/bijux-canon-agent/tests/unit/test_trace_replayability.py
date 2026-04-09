from __future__ import annotations

from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle
from bijux_canon_agent.traces import ReplayMetadata
from bijux_canon_agent.traces.replayability import (
    enforce_replayable_temperature,
    has_required_replay_metadata,
    resolve_contract_version,
)
import pytest
from tests.utils.trace_helpers import default_model_metadata


def test_resolve_contract_version_defaults_when_metadata_missing() -> None:
    assert resolve_contract_version(None) == CONTRACT_VERSION


def test_has_required_replay_metadata_requires_finalize_convergence_hash() -> None:
    metadata = ReplayMetadata(
        input_hash="input",
        config_hash="config",
        model_id="model",
        model_metadata=default_model_metadata(),
    )

    assert (
        has_required_replay_metadata(
            metadata,
            phase=PipelineLifecycle.FINALIZE.value,
            convergence_hash="stable-hash",
        )
        is False
    )


def test_has_required_replay_metadata_accepts_complete_payload() -> None:
    metadata = ReplayMetadata(
        input_hash="input",
        config_hash="config",
        model_id="model",
        convergence_hash="stable-hash",
        model_metadata=default_model_metadata(),
    )

    assert has_required_replay_metadata(
        metadata,
        phase=PipelineLifecycle.FINALIZE.value,
        convergence_hash="stable-hash",
    )


def test_enforce_replayable_temperature_rejects_non_deterministic_replay() -> None:
    with pytest.raises(
        RuntimeError, match="Trace marked replayable despite non-zero temperature"
    ):
        enforce_replayable_temperature(temperature=0.3, replayable=True)
