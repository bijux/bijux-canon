from __future__ import annotations

from unittest.mock import Mock

import pytest

from bijux_canon_agent.agents.validator.validation_issues import (
    collect_extra_key_warning,
    run_custom_validation_issues,
)


class _Agent:
    def __init__(self) -> None:
        self.custom_validator = object()
        self.config = {"strict": True}
        self.logger = Mock()
        self.logger_manager = Mock()


@pytest.mark.asyncio
async def test_run_custom_validation_issues_collects_user_results() -> None:
    agent = _Agent()
    audit: dict[str, object] = {}

    async def _runner(*_args: object) -> dict[str, object]:
        return {
            "errors": ["custom error"],
            "warnings": ["custom warning"],
            "details": {"source": "custom"},
        }

    errors, warnings = await run_custom_validation_issues(
        agent,
        data={"value": 1},
        audit=audit,
        run_custom_validator=_runner,
    )

    assert errors == ["custom error"]
    assert warnings == ["custom warning"]
    assert audit == {"custom_validator": {"source": "custom"}}


@pytest.mark.asyncio
async def test_run_custom_validation_issues_converts_failures_to_errors() -> None:
    agent = _Agent()

    async def _runner(*_args: object) -> dict[str, object]:
        raise RuntimeError("boom")

    errors, warnings = await run_custom_validation_issues(
        agent,
        data={"value": 1},
        audit={},
        run_custom_validator=_runner,
    )

    assert errors == ["Custom validator failed: boom"]
    assert warnings == []


def test_collect_extra_key_warning_reports_unexpected_keys() -> None:
    warning = collect_extra_key_warning(
        data={"known": 1, "extra": 2},
        schema_keys={"known"},
        data_keys={"known", "extra"},
        strict=True,
        allow_extra=False,
    )

    assert warning == "Unexpected extra keys: ['extra']"


def test_collect_extra_key_warning_skips_non_strict_validation() -> None:
    assert (
        collect_extra_key_warning(
            data={"known": 1, "extra": 2},
            schema_keys={"known"},
            data_keys={"known", "extra"},
            strict=False,
            allow_extra=False,
        )
        is None
    )
