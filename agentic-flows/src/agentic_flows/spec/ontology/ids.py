# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/ontology/ids.py."""

from __future__ import annotations


class FlowID(str):
    """Stable flow identifier; wrong value breaks trace linkage."""


class AgentID(str):
    """Stable agent identifier; wrong value breaks provenance."""


class ToolID(str):
    """Stable tool identifier; wrong value breaks tool audit."""


class ActionID(str):
    """Stable action identifier; wrong value breaks action audit."""


class ArtifactID(str):
    """Artifact identifier; wrong value breaks artifact lineage."""


class EvidenceID(str):
    """Evidence identifier; wrong value breaks verification linkage."""


class StepID(str):
    """Step identifier; wrong value breaks step ordering and replay."""


class ClaimID(str):
    """Claim identifier; wrong value breaks claim provenance."""


class BundleID(str):
    """Reasoning bundle identifier; wrong value breaks trace grouping."""


class RuleID(str):
    """Verification rule identifier; wrong value breaks enforcement."""


class RequestID(str):
    """Request identifier; wrong value breaks request traceability."""


class ContractID(str):
    """Contract identifier; wrong value breaks contract resolution."""


class GateID(str):
    """Gate identifier; wrong value breaks verification gating."""


class ResolverID(str):
    """Resolver identifier; wrong value breaks planner attribution."""


class VersionID(str):
    """Version identifier; wrong value breaks compatibility checks."""


class DatasetID(str):
    """Dataset identifier; wrong value breaks dataset governance."""


class TenantID(str):
    """Tenant identifier; wrong value breaks isolation guarantees."""


class InputsFingerprint(str):
    """Inputs fingerprint; wrong value breaks determinism seeding."""


class ContentHash(str):
    """Content hash; wrong value breaks integrity verification."""


class EnvironmentFingerprint(str):
    """Environment fingerprint; wrong value breaks drift detection."""


class PlanHash(str):
    """Plan hash; wrong value breaks replay equivalence."""


class PolicyFingerprint(str):
    """Policy hash; wrong value breaks verification integrity."""


class RunID(str):
    """Run identifier; wrong value breaks persistence lookup."""


__all__ = [
    "FlowID",
    "AgentID",
    "ToolID",
    "ActionID",
    "ArtifactID",
    "EvidenceID",
    "StepID",
    "ClaimID",
    "BundleID",
    "RuleID",
    "RequestID",
    "ContractID",
    "GateID",
    "ResolverID",
    "VersionID",
    "DatasetID",
    "TenantID",
    "InputsFingerprint",
    "ContentHash",
    "EnvironmentFingerprint",
    "PlanHash",
    "PolicyFingerprint",
    "RunID",
]
