# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.domain.nd.randomness import validate_randomness_payload


def validate_execution_request_payload(payload: object) -> None:
    contract = getattr(payload, "execution_contract", None)
    execution_mode = getattr(payload, "execution_mode", None)
    execution_intent = getattr(payload, "execution_intent", None)
    randomness_profile = getattr(payload, "randomness_profile", None)
    execution_budget = getattr(payload, "execution_budget", None)

    if contract is ExecutionContract.NON_DETERMINISTIC:
        validate_randomness_payload(payload)
    if contract is ExecutionContract.NON_DETERMINISTIC and execution_budget is None:
        raise ValueError("execution_budget required for non_deterministic execution")
    if not isinstance(execution_intent, ExecutionIntent):
        raise ValueError("execution_intent must be a known ExecutionIntent")
    if not isinstance(execution_mode, ExecutionMode):
        raise ValueError("execution_mode must be strict|bounded|exploratory")

    nd_fields = (
        "nd_profile",
        "nd_target_recall",
        "nd_latency_budget_ms",
        "nd_witness_rate",
        "nd_witness_sample_k",
        "nd_witness_mode",
        "nd_build_on_demand",
        "nd_candidate_k",
        "nd_diversity_lambda",
        "nd_normalize_vectors",
        "nd_normalize_query",
        "nd_outlier_threshold",
        "nd_low_signal_margin",
        "nd_adaptive_k",
        "nd_low_signal_refuse",
        "nd_replay_strict",
        "nd_warmup_queries",
        "nd_incremental_index",
        "nd_max_candidates",
        "nd_max_index_memory_mb",
        "nd_m",
        "nd_ef_construction",
        "nd_ef_search",
        "nd_max_ef_search",
        "nd_space",
    )
    if contract is ExecutionContract.DETERMINISTIC:
        if execution_mode is not ExecutionMode.STRICT:
            raise ValueError("deterministic executions require strict mode")
        if any(
            getattr(payload, field, None) not in (None, False) for field in nd_fields
        ):
            raise ValueError("nd_* settings require non_deterministic execution")
        if getattr(payload, "nd_two_stage", True) is False:
            raise ValueError("nd_* settings require non_deterministic execution")
        return

    if execution_mode is ExecutionMode.STRICT:
        raise ValueError(
            "non_deterministic executions require bounded or exploratory mode"
        )
    nd_profile = getattr(payload, "nd_profile", None)
    if nd_profile not in {None, "fast", "balanced", "accurate"}:
        raise ValueError("nd_profile must be fast|balanced|accurate")
    nd_target_recall = getattr(payload, "nd_target_recall", None)
    if nd_target_recall is not None and not (0.0 < nd_target_recall <= 1.0):
        raise ValueError("nd_target_recall must be within (0,1]")
    nd_latency_budget_ms = getattr(payload, "nd_latency_budget_ms", None)
    if nd_latency_budget_ms is not None and nd_latency_budget_ms <= 0:
        raise ValueError("nd_latency_budget_ms must be positive")
    nd_witness_rate = getattr(payload, "nd_witness_rate", None)
    if nd_witness_rate is not None and not (0.0 < nd_witness_rate <= 1.0):
        raise ValueError("nd_witness_rate must be within (0,1]")
    nd_witness_mode = getattr(payload, "nd_witness_mode", None)
    if nd_witness_mode not in {None, "off", "sample", "full"}:
        raise ValueError("nd_witness_mode must be off|sample|full")
    nd_witness_sample_k = getattr(payload, "nd_witness_sample_k", None)
    if nd_witness_sample_k is not None and nd_witness_sample_k <= 0:
        raise ValueError("nd_witness_sample_k must be positive")
    nd_max_index_memory_mb = getattr(payload, "nd_max_index_memory_mb", None)
    if nd_max_index_memory_mb is not None and nd_max_index_memory_mb <= 0:
        raise ValueError("nd_max_index_memory_mb must be positive")
    nd_m = getattr(payload, "nd_m", None)
    if nd_m is not None and nd_m <= 0:
        raise ValueError("nd_m must be positive")
    nd_ef_construction = getattr(payload, "nd_ef_construction", None)
    if nd_ef_construction is not None and nd_ef_construction <= 0:
        raise ValueError("nd_ef_construction must be positive")
    nd_ef_search = getattr(payload, "nd_ef_search", None)
    if nd_ef_search is not None and nd_ef_search <= 0:
        raise ValueError("nd_ef_search must be positive")
    nd_max_ef_search = getattr(payload, "nd_max_ef_search", None)
    if nd_max_ef_search is not None and nd_max_ef_search <= 0:
        raise ValueError("nd_max_ef_search must be positive")
    nd_low_signal_margin = getattr(payload, "nd_low_signal_margin", None)
    if nd_low_signal_margin is not None and nd_low_signal_margin <= 0:
        raise ValueError("nd_low_signal_margin must be positive")
    nd_space = getattr(payload, "nd_space", None)
    if nd_space not in {None, "l2", "cosine", "ip"}:
        raise ValueError("nd_space must be l2|cosine|ip")
    if randomness_profile:
        validate_randomness_payload(payload)
