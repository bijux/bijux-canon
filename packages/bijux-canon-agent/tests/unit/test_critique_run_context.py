from __future__ import annotations

from bijux_canon_agent.agents.critique.run_context import (
    build_critique_run_input,
    extract_critique_text,
    extract_source_text,
)


def test_extract_critique_text_flattens_summary_payloads() -> None:
    context = {
        "summary": {
            "executive_summary": "Overview",
            "key_points": ["One", "Two"],
            "content": "Details",
        }
    }

    assert extract_critique_text(context) == "Overview One Two Details"


def test_extract_source_text_prefers_explicit_source_text() -> None:
    context = {"source_text": "Source", "text": "Fallback"}

    assert extract_source_text(context) == "Source"


def test_build_critique_run_input_uses_text_hash_for_cache_key() -> None:
    critique_input = build_critique_run_input({"text": "hello"})

    assert critique_input is not None
    assert critique_input.text == "hello"
    assert len(critique_input.cache_key) == 64
