from __future__ import annotations

from bijux_canon_agent.agents.validator.run_context import (
    apply_pre_hook,
    build_validation_run_context,
    cache_schema,
)


def test_build_validation_run_context_extracts_data_and_hash() -> None:
    run_context = build_validation_run_context(
        {"context_id": "ctx-1", "data": {"value": 1}},
        {"type": "object"},
    )

    assert run_context.context_id == "ctx-1"
    assert run_context.data == {"value": 1}
    assert len(run_context.schema_hash) == 64


def test_apply_pre_hook_reports_success(logger_manager) -> None:
    data, error = apply_pre_hook(
        {"value": 1},
        pre_hook=lambda payload: {**payload, "normalized": True},
        logger=logger_manager.get_logger(),
        logger_manager=logger_manager,
    )

    assert error is None
    assert data["normalized"] is True


def test_cache_schema_stores_schema_snapshot(logger_manager) -> None:
    schema_cache: dict[str, dict[str, object]] = {}
    cache_schema(
        schema_hash="abc",
        schema={"type": "object"},
        schema_cache=schema_cache,
        logger=logger_manager.get_logger(),
        logger_manager=logger_manager,
    )

    assert schema_cache["abc"] == {"type": "object"}
