# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_runtime.core.authority import evaluate_verification
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.ontology.ids import AgentID, BundleID, RuleID

pytestmark = pytest.mark.unit


class _RegistryStub:
    def __init__(self, violations: list[RuleID]) -> None:
        self._violations = violations

    def evaluate(self, *_args, **_kwargs) -> tuple[list[RuleID], int, list[RuleID]]:
        return list(self._violations), 0, []


def _bundle() -> ReasoningBundle:
    return ReasoningBundle(
        spec_version="v1",
        bundle_id=BundleID("bundle-a"),
        claims=(),
        steps=(),
        evidence_ids=(),
        producer_agent_id=AgentID("agent-a"),
    )


def test_evaluate_verification_escalates_matching_policy_rule(
    baseline_policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = replace(
        baseline_policy,
        escalate_on=(RuleID("rule-escalate"),),
    )
    monkeypatch.setattr(
        "bijux_canon_runtime.core.authority.default_rule_registry",
        lambda: _RegistryStub([RuleID("rule-escalate")]),
    )

    result = evaluate_verification(_bundle(), (), (), policy)

    assert result.status == "ESCALATE"
    assert result.reason == "policy_escalate_on"


def test_evaluate_verification_fails_matching_policy_rule(
    baseline_policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = replace(
        baseline_policy,
        fail_on=(RuleID("rule-fail"),),
    )
    monkeypatch.setattr(
        "bijux_canon_runtime.core.authority.default_rule_registry",
        lambda: _RegistryStub([RuleID("rule-fail")]),
    )

    result = evaluate_verification(_bundle(), (), (), policy)

    assert result.status == "FAIL"
    assert result.reason == "policy_fail_on"
