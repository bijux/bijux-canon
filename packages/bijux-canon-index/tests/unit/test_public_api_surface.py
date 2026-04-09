# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import importlib
import inspect

EXPECTED = {
    "bijux_canon_index.core.types.base": {
        "Document",
        "Chunk",
        "Vector",
        "ModelSpec",
        "ExecutionRequest",
        "ExecutionBudget",
        "NDSettings",
        "Result",
        "ExecutionArtifact",
    },
    "bijux_canon_index.core.errors": {
        "BijuxError",
        "ValidationError",
        "InvariantError",
        "NotFoundError",
        "ConflictError",
        "ConfigurationError",
        "DeterminismViolationError",
        "BackendUnavailableError",
        "CorruptArtifactError",
        "AtomicityViolationError",
        "AuthzDeniedError",
        "BackendDivergenceError",
        "BackendCapabilityError",
        "NDExecutionUnavailableError",
        "AnnIndexBuildError",
        "AnnQueryError",
        "AnnBudgetError",
        "PluginError",
        "PluginLoadError",
        "PluginTimeoutError",
        "ReplayNotSupportedError",
        "BudgetExceededError",
        "mark_retryable",
        "FailureKind",
        "classify_failure",
        "retry_with_policy",
        "FAILURE_ACTIONS",
        "action_for_failure",
    },
    "bijux_canon_index.core.canon": {"canon", "CANON_VERSION"},
    "bijux_canon_index.core.identity.ids": {"fingerprint", "make_id", "CANON_VERSION"},
    "bijux_canon_index.core.contracts.execution_contract": {"ExecutionContract"},
    "bijux_canon_index.core.runtime.vector_execution": {
        "VectorExecution",
        "RandomnessProfile",
        "derive_execution_id",
        "execution_signature",
    },
    "bijux_canon_index.domain.requests.execution_plan": {
        "build_execution_plan",
        "run_plan",
    },
    "bijux_canon_index.domain.requests.comparison": {"ExecutionComparator"},
    "bijux_canon_index.core.invariants": {
        "ALLOWED_METRICS",
        "validate_execution_artifact",
    },
    "bijux_canon_index.contracts.resources": {
        "ExecutionResources",
        "BackendCapabilities",
        "VectorSource",
        "ExecutionLedger",
    },
    "bijux_canon_index.contracts.tx": {"Tx"},
    "bijux_canon_index.contracts.authz": {"Authz", "AllowAllAuthz", "DenyAllAuthz"},
    "bijux_canon_index.application.engine": {"VectorExecutionEngine"},
}


def _public_names(module):
    names: set[str] = set()
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        obj_module = getattr(obj, "__module__", None)
        if obj_module == module.__name__:
            names.add(name)
        elif (
            not inspect.ismodule(obj)
            and obj.__class__.__module__ == "builtins"
            and obj_module is None
        ):
            names.add(name)
    return names


def test_public_surface_is_stable():
    for module_path, expected in EXPECTED.items():
        module = importlib.import_module(module_path)
        assert _public_names(module) == expected
