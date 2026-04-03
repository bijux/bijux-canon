"""Ensure AgentOutputSchema exposes attribute and mapping access."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.models.contract import AgentOutputSchema


def test_agent_output_schema_accessors() -> None:
    """AgentOutputSchema must allow attribute and mapping semantics."""
    schema = AgentOutputSchema(
        text="doc",
        artifacts={"plan": "value"},
        scores={"relevance": 1.0},
        confidence=0.88,
        metadata={"contract_version": CONTRACT_VERSION},
    )
    assert schema.artifacts == schema.artifacts
    assert schema.confidence == 0.88
    as_dict = schema.model_dump()
    assert "text" in as_dict
    assert schema.artifacts["plan"] == "value"
    as_dict = schema.model_dump()
    assert as_dict["text"] == schema.text


def test_agent_output_schema_is_frozen() -> None:
    """AgentOutputSchema enforces immutability once constructed."""
    schema = AgentOutputSchema(
        text="immutable",
        artifacts={},
        scores={"ok": 1.0},
        confidence=0.5,
        metadata={"contract_version": CONTRACT_VERSION},
    )
    with pytest.raises(ValidationError):
        schema.text = "mutable"


def test_agent_output_schema_blocks_mapping_access() -> None:
    """AgentOutputSchema should enforce attribute-only access internally."""
    schema = AgentOutputSchema(
        text="guarded",
        artifacts={"plan": "value"},
        scores={"relevance": 1.0},
        confidence=0.88,
        metadata={"contract_version": CONTRACT_VERSION},
    )
    with pytest.raises(TypeError):
        _ = schema["text"]
    with pytest.raises(TypeError):
        _ = schema.get("text")
