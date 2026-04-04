# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_runtime import core
from bijux_canon_runtime.core import ids


def test_core_identifier_exports_are_explicit_and_stable() -> None:
    expected = {
        "ActionID",
        "AgentID",
        "ArtifactID",
        "BundleID",
        "ClaimID",
        "ContentHash",
        "ContractID",
        "DatasetID",
        "EnvironmentFingerprint",
        "EvidenceID",
        "FlowID",
        "GateID",
        "InputsFingerprint",
        "PlanHash",
        "PolicyFingerprint",
        "RequestID",
        "ResolverID",
        "RuleID",
        "RunID",
        "StepID",
        "TenantID",
        "ToolID",
        "VersionID",
    }
    assert set(ids.__all__) == expected
    assert expected <= set(core.__all__)
