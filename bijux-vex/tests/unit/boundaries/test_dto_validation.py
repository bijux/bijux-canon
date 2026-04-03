# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.execution_intent import ExecutionIntent

import pytest

from pydantic import ValidationError

from bijux_vex.boundaries.pydantic_edges.models import (
    CreateRequest,
    ExplainRequest,
    IngestRequest,
    ExecutionRequestPayload,
)
from bijux_vex.core.contracts.execution_contract import ExecutionContract


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        CreateRequest(name="demo", extra="nope")  # type: ignore[arg-type]


def test_ingest_length_mismatch():
    with pytest.raises(ValidationError):
        IngestRequest(documents=["a", "b"], vectors=[[0.0]])


def test_ingest_requires_vectors_or_embed_model():
    with pytest.raises(ValidationError):
        IngestRequest(documents=["a"])


def test_execute_requires_request_or_vector():
    with pytest.raises(ValidationError):
        ExecutionRequestPayload(
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
        )


def test_non_deterministic_requires_randomness():
    with pytest.raises(ValidationError):
        ExecutionRequestPayload(
            execution_contract=ExecutionContract.NON_DETERMINISTIC,
            execution_intent=ExecutionIntent.EXPLORATORY_SEARCH,
            vector=(0.0,),
        )


def test_explain_requires_result_id():
    with pytest.raises(ValidationError):
        ExplainRequest(result_id="")
