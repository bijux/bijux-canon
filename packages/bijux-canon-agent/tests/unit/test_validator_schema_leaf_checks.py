from __future__ import annotations

from unittest.mock import Mock

from bijux_canon_agent.agents.validator.rules.schema_leaf_checks import (
    validate_list_branch,
    validate_terminal_branch,
)


class _Agent:
    def __init__(self) -> None:
        self.logger = Mock()
        self.logger_manager = Mock()


def test_validate_list_branch_reports_type_mismatch() -> None:
    agent = _Agent()

    errors, audit = validate_list_branch(
        agent,
        data="not-a-list",
        schema=[str],
        path="items",
        tags={"stage": "validation", "path": "items"},
        validate_recursive=lambda *_args: ([], {}),
    )

    assert errors == ["items: Expected list, got str"]
    assert audit == {
        "items": {
            "error": "type_mismatch",
            "expected": "list",
            "actual": "str",
        }
    }


def test_validate_list_branch_delegates_to_recursive_validator() -> None:
    agent = _Agent()

    errors, audit = validate_list_branch(
        agent,
        data=["one", "two"],
        schema=[str],
        path="items",
        tags={"stage": "validation", "path": "items"},
        validate_recursive=lambda _agent, item, _schema, item_path: (
            [f"{item_path}:{item}"],
            {"value": item},
        ),
    )

    assert errors == ["items[0]:one", "items[1]:two"]
    assert audit == {"items[0]": {"value": "one"}, "items[1]": {"value": "two"}}


def test_validate_terminal_branch_accepts_matching_type() -> None:
    agent = _Agent()

    errors, audit = validate_terminal_branch(
        agent,
        data=3,
        schema=int,
        path="count",
        tags={"stage": "validation", "path": "count"},
    )

    assert errors == []
    assert audit == {"count": {"value": 3, "expected": "int", "type": "int"}}
