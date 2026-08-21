# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Explicit construction of versioned canonical package adapters."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
from typing import Any

from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.runtime.execution.canonical_adapters import (
    CanonicalAgentAdapterV1,
    CanonicalReasonAdapterV1,
    CanonicalRetrievalAdapterV1,
    CanonicalVectorContractAdapterV1,
)

# Focused runtime tests may inject deterministic boundary outcomes. Production
# construction never discovers callables from package roots.
agent_runner_override: Callable[..., Any] | None = None
retrieval_runner_override: Callable[..., Any] | None = None
reasoning_runner_override: Callable[..., Any] | None = None
vector_contract_enforcer_override: Callable[..., Any] | None = None


def load_agent_runner() -> Callable[..., Any]:
    """Construct the declared canonical agent adapter."""
    if agent_runner_override is not None:
        return agent_runner_override
    settings = resolve_runtime_configuration(environment=os.environ)
    working_root = settings.working_root or Path.cwd()
    return CanonicalAgentAdapterV1(working_root=working_root).run


def load_retrieval_runner() -> Callable[..., Any]:
    """Construct the declared canonical persisted-index adapter."""
    if retrieval_runner_override is not None:
        return retrieval_runner_override
    settings = resolve_runtime_configuration(environment=os.environ)
    return CanonicalRetrievalAdapterV1(
        index_path=settings.retrieval_index_path
    ).retrieve


def load_reasoning_runner() -> Callable[..., Any]:
    """Construct the declared canonical reason adapter."""
    if reasoning_runner_override is not None:
        return reasoning_runner_override
    return CanonicalReasonAdapterV1().reason


def load_vector_contract_enforcer() -> Callable[..., Any]:
    """Construct the declared canonical index ABI adapter."""
    if vector_contract_enforcer_override is not None:
        return vector_contract_enforcer_override
    return CanonicalVectorContractAdapterV1().enforce


__all__ = [
    "load_agent_runner",
    "load_reasoning_runner",
    "load_retrieval_runner",
    "load_vector_contract_enforcer",
]
