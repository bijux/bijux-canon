# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bijux_vex.boundaries.pydantic_edges.validators import (
    validate_execution_request_payload,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode


def _payload(**overrides):
    base = dict(
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_mode=ExecutionMode.STRICT,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
        randomness_profile=None,
        execution_budget=None,
        nd_profile=None,
        nd_target_recall=None,
        nd_latency_budget_ms=None,
        nd_witness_rate=None,
        nd_witness_sample_k=None,
        nd_witness_mode=None,
        nd_build_on_demand=False,
        nd_candidate_k=None,
        nd_diversity_lambda=None,
        nd_normalize_vectors=False,
        nd_normalize_query=False,
        nd_outlier_threshold=None,
        nd_low_signal_margin=None,
        nd_adaptive_k=False,
        nd_low_signal_refuse=False,
        nd_replay_strict=False,
        nd_warmup_queries=None,
        nd_incremental_index=None,
        nd_max_candidates=None,
        nd_max_index_memory_mb=None,
        nd_two_stage=True,
        nd_m=None,
        nd_ef_construction=None,
        nd_ef_search=None,
        nd_max_ef_search=None,
        nd_space=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_validator_rejects_nd_without_randomness():
    payload = _payload(
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=SimpleNamespace(max_latency_ms=1),
    )
    with pytest.raises(ValueError, match="randomness_profile required"):
        validate_execution_request_payload(payload)


def test_validator_rejects_nd_settings_for_deterministic():
    payload = _payload(nd_two_stage=False)
    with pytest.raises(ValueError, match="nd_\\* settings require non_deterministic"):
        validate_execution_request_payload(payload)


def test_validator_accepts_minimal_nd():
    payload = _payload(
        execution_contract=ExecutionContract.NON_DETERMINISTIC,
        execution_mode=ExecutionMode.BOUNDED,
        execution_budget=SimpleNamespace(max_latency_ms=1),
        randomness_profile=SimpleNamespace(
            seed=1, sources=("seed",), non_replayable=False
        ),
    )
    validate_execution_request_payload(payload)
