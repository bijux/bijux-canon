# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Explicit construction of versioned canonical package adapters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
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


def load_agent_runner(
    configuration: RuntimeConfiguration,
) -> Callable[..., Any]:
    """Construct the declared canonical agent adapter."""
    if agent_runner_override is not None:
        return agent_runner_override
    working_root = configuration.require_workspace_layout().root
    return CanonicalAgentAdapterV1(working_root=working_root).run


def load_retrieval_runner(
    configuration: RuntimeConfiguration,
) -> Callable[..., Any]:
    """Construct the declared canonical persisted-index adapter."""
    if retrieval_runner_override is not None:
        return retrieval_runner_override
    return CanonicalRetrievalAdapterV1(
        index_path=configuration.require_workspace_layout().index_root
    ).retrieve


def load_reasoning_runner(
    _configuration: RuntimeConfiguration,
) -> Callable[..., Any]:
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
