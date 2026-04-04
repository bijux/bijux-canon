from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bijux_canon_agent.agents.critique.criteria_execution import evaluate_rule_criteria
from bijux_canon_agent.agents.critique.reporting import create_criterion_result


@dataclass
class _Agent:
    penalties: dict[str, float]

    def _create_result(
        self,
        name: str,
        passed: bool,
        issues: list[str],
        severity: str | None = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        return create_criterion_result(
            name,
            passed,
            issues,
            suggestion_map={name: f"Fix {name}"},
            severity_map={name: "Major"},
            severity=severity,
            confidence=confidence,
        )


def test_evaluate_rule_criteria_collects_failures() -> None:
    agent = _Agent(penalties={"criterion": 0.25})
    state = evaluate_rule_criteria(
        agent,
        text="body",
        context={},
        criteria=["criterion"],
        rules={
            "criterion": lambda *_args: create_criterion_result(
                "criterion",
                False,
                ["broken"],
                suggestion_map={"criterion": "Fix criterion"},
                severity_map={"criterion": "Major"},
            )
        },
    )

    assert state.score == 0.75
    assert state.issues == ["broken"]
    assert state.per_critique[0].result == "FAIL"


def test_evaluate_rule_criteria_records_missing_rules() -> None:
    agent = _Agent(penalties={})
    state = evaluate_rule_criteria(
        agent,
        text="body",
        context={},
        criteria=["missing"],
        rules={},
    )

    assert state.score == 1.0
    assert state.warnings == ["Criterion 'missing' not implemented"]


def test_evaluate_rule_criteria_converts_exceptions_to_issues() -> None:
    agent = _Agent(penalties={"criterion": 0.1})

    def _boom(*_args: object) -> dict[str, Any]:
        raise RuntimeError("failure")

    state = evaluate_rule_criteria(
        agent,
        text="body",
        context={},
        criteria=["criterion"],
        rules={"criterion": _boom},
    )

    assert state.score == 0.9
    assert state.issues == ["Criterion criterion failed: failure"]
    assert state.per_critique[0].severity == "Critical"
