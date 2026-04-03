# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/datasets/retrieval_request.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.ontology.ids import ContractID, RequestID


@dataclass(frozen=True)
class RetrievalRequest:
    """Retrieval request; misuse breaks evidence sourcing."""

    spec_version: str
    request_id: RequestID
    query: str
    vector_contract_id: ContractID
    top_k: int
    scope: str


__all__ = ["RetrievalRequest"]
