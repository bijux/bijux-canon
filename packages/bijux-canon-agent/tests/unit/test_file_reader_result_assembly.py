from __future__ import annotations

from bijux_canon_agent.agents.file_reader.result_assembly import (
    apply_extra_analyzers,
    apply_post_hook,
    finalize_read_result,
)


def test_apply_extra_analyzers_merges_results(logger_manager) -> None:
    logger = logger_manager.get_logger()
    read_result = {"text": "hello"}

    def add_summary(result: dict[str, object]) -> dict[str, object]:
        return {"summary": f"len={len(str(result['text']))}"}

    def add_tags(_: dict[str, object]) -> dict[str, object]:
        return {"tags": ["note"]}

    apply_extra_analyzers(
        read_result,
        [add_summary, add_tags],
        logger=logger,
        logger_manager=logger_manager,
    )

    assert read_result["enrichments"] == {
        "summary": "len=5",
        "tags": ["note"],
    }


def test_apply_post_hook_returns_original_result_on_failure(logger_manager) -> None:
    logger = logger_manager.get_logger()
    read_result = {"text": "hello"}

    def fail_post_hook(
        _context: dict[str, object],
        _result: dict[str, object],
    ) -> dict[str, object]:
        raise RuntimeError("boom")

    updated_result = apply_post_hook(
        {"file_path": "note.txt"},
        read_result,
        post_hook=fail_post_hook,
        logger=logger,
        logger_manager=logger_manager,
    )

    assert updated_result is read_result


def test_finalize_read_result_attaches_audit_and_enrichments(logger_manager) -> None:
    logger = logger_manager.get_logger()
    read_result = {"text": "hello world"}

    def post_hook(
        _context: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object]:
        return {**result, "post_processed": True}

    finalized = finalize_read_result(
        read_result,
        context={"file_path": "note.txt"},
        post_hook=post_hook,
        file_path="note.txt",
        context_id="ctx-1",
        file_suffix="txt",
        agent_version="2.0.0",
        agent_id="agent-1",
        cache_enabled=True,
        async_io=True,
        logger=logger,
        logger_manager=logger_manager,
    )

    assert finalized["post_processed"] is True
    assert finalized["n_chars"] == 11
    assert finalized["file_agent_audit"]["context_id"] == "ctx-1"
