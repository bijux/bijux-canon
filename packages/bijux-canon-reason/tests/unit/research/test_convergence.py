# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Bounded research convergence tests."""

from __future__ import annotations

import pytest

from bijux_canon_reason.research import (
    ConvergenceDecision,
    ConvergenceError,
    ConvergenceErrorCode,
    ConvergenceOutcome,
    ConvergencePolicy,
    ConvergenceReason,
    ConvergenceService,
    create_convergence_observation,
)


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _observation(
    iteration: int = 1,
    *,
    graph: str = "a",
    coverage: float = 0.5,
    verified: int = 1,
    required: int = 2,
    gaps: int = 1,
    value: float = 0.1,
    tools: int = 1,
    tokens: int = 100,
    elapsed: int = 100,
    cancelled: bool = False,
    insufficient: bool = False,
):
    return create_convergence_observation(
        iteration=iteration,
        graph_artifact_id=_artifact(graph),
        coverage=coverage,
        verified_answerable_claims=verified,
        required_claims=required,
        blocking_gap_count=gaps,
        new_evidence_count=1,
        marginal_evidence_value=value,
        cumulative_tool_calls=tools,
        cumulative_tokens=tokens,
        cumulative_elapsed_ms=elapsed,
        cancellation_requested=cancelled,
        explicit_insufficiency=insufficient,
    )


def test_continues_only_when_no_terminal_condition_holds() -> None:
    decision = ConvergenceService().evaluate((_observation(),))

    assert not decision.stop
    assert decision.outcome is ConvergenceOutcome.continue_research
    assert decision.reasons == (ConvergenceReason.continue_research,)


def test_integer_metric_inputs_have_canonical_float_identity() -> None:
    observation = create_convergence_observation(
        iteration=1,
        graph_artifact_id=_artifact("a"),
        coverage=0,
        verified_answerable_claims=0,
        required_claims=0,
        blocking_gap_count=1,
        new_evidence_count=0,
        marginal_evidence_value=0,
        cumulative_tool_calls=1,
        cumulative_tokens=0,
        cumulative_elapsed_ms=1,
        explicit_insufficiency=True,
    )

    assert observation.coverage == 0.0
    assert observation.marginal_evidence_value == 0.0


def test_coverage_and_verified_answerability_converge() -> None:
    decision = ConvergenceService().evaluate(
        (_observation(coverage=0.9, verified=2, required=2, gaps=0),)
    )
    restarted = ConvergenceDecision.model_validate_json(decision.model_dump_json())

    assert restarted == decision
    assert decision.stop
    assert decision.outcome is ConvergenceOutcome.converged
    assert ConvergenceReason.coverage_and_answerability in decision.reasons


def test_stable_graph_and_diminishing_value_stop_insufficient_research() -> None:
    stable = ConvergenceService().evaluate(
        (
            _observation(1, graph="a", tools=1, tokens=100, elapsed=100),
            _observation(2, graph="a", tools=2, tokens=200, elapsed=200),
        )
    )
    diminishing = ConvergenceService().evaluate(
        (
            _observation(1, graph="a", value=0.001, tools=1),
            _observation(
                2,
                graph="b",
                value=0.001,
                tools=2,
                tokens=200,
                elapsed=200,
            ),
        )
    )

    assert stable.outcome is ConvergenceOutcome.insufficient
    assert stable.reasons == (ConvergenceReason.stable_graph,)
    assert diminishing.outcome is ConvergenceOutcome.insufficient
    assert diminishing.reasons == (ConvergenceReason.diminishing_evidence_value,)


@pytest.mark.parametrize(
    ("policy", "observations", "reason"),
    [
        (
            ConvergencePolicy(max_iterations=2),
            (
                _observation(1, graph="a"),
                _observation(2, graph="b", tools=2, tokens=200, elapsed=200),
            ),
            ConvergenceReason.iteration_limit,
        ),
        (
            ConvergencePolicy(max_tool_calls=1),
            (_observation(tools=1),),
            ConvergenceReason.tool_limit,
        ),
        (
            ConvergencePolicy(max_tokens=100),
            (_observation(tokens=100),),
            ConvergenceReason.token_limit,
        ),
        (
            ConvergencePolicy(max_elapsed_ms=100),
            (_observation(elapsed=100),),
            ConvergenceReason.time_limit,
        ),
    ],
)
def test_each_resource_limit_stops_without_another_iteration(
    policy: ConvergencePolicy, observations: tuple, reason: ConvergenceReason
) -> None:
    decision = ConvergenceService(policy).evaluate(observations)

    assert decision.stop
    assert decision.outcome is ConvergenceOutcome.budget_exhausted
    assert reason in decision.reasons


def test_cancellation_and_explicit_insufficiency_have_terminal_precedence() -> None:
    cancelled = ConvergenceService().evaluate((_observation(cancelled=True),))
    insufficient = ConvergenceService().evaluate((_observation(insufficient=True),))

    assert cancelled.outcome is ConvergenceOutcome.cancelled
    assert cancelled.reasons == (ConvergenceReason.cancelled,)
    assert insufficient.outcome is ConvergenceOutcome.insufficient
    assert insufficient.reasons == (ConvergenceReason.explicit_insufficiency,)


def test_invalid_or_post_terminal_history_fails_closed() -> None:
    service = ConvergenceService()
    with pytest.raises(ConvergenceError) as empty:
        service.evaluate(())
    assert empty.value.code is ConvergenceErrorCode.empty_history

    with pytest.raises(ConvergenceError) as sequence:
        service.evaluate((_observation(2),))
    assert sequence.value.code is ConvergenceErrorCode.nonsequential_iteration

    with pytest.raises(ConvergenceError) as regressed:
        service.evaluate(
            (
                _observation(1, tools=2, tokens=200, elapsed=200),
                _observation(2, graph="b", tools=1, tokens=100, elapsed=100),
            )
        )
    assert regressed.value.code is ConvergenceErrorCode.cumulative_usage_regressed

    with pytest.raises(ConvergenceError) as after_terminal:
        service.evaluate(
            (
                _observation(1, coverage=0.9, verified=2, required=2, gaps=0),
                _observation(2, graph="b", tools=2, tokens=200, elapsed=200),
            )
        )
    assert after_terminal.value.code is (
        ConvergenceErrorCode.history_after_terminal_decision
    )
