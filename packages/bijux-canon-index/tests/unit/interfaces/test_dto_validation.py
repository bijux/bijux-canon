# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.interfaces.schemas.models import (
    CreateRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)
from pydantic_core import ValidationError
import pytest


def test_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateRequest(name="demo", extra="nope")


def test_ingest_length_mismatch() -> None:
    with pytest.raises(ValidationError):
        IngestRequest(documents=["a", "b"], vectors=[[0.0]])


def test_ingest_requires_vectors_or_embed_model() -> None:
    with pytest.raises(ValidationError):
        IngestRequest(documents=["a"])


def test_execute_requires_request_or_vector() -> None:
    with pytest.raises(ValidationError):
        ExecutionRequestPayload(
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
        )


def test_non_deterministic_requires_randomness() -> None:
    with pytest.raises(ValidationError):
        ExecutionRequestPayload(
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            vector=(0.0,),
        )


def test_explain_requires_result_id() -> None:
    with pytest.raises(ValidationError):
        ExplainRequest(result_id="")
