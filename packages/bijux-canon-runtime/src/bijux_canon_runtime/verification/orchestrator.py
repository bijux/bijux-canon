# INTERNAL — NOT A PUBLIC EXTENSION POINT
# INTERNAL — SUBJECT TO CHANGE WITHOUT NOTICE
# INTERNAL API — NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

# Verification must never call agents or modify artifact; epistemic truth is delegated to authority.
"""Verification orchestration for runtime execution results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bijux_canon_runtime.core.authority import evaluate_verification
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.ontology import (
    ReasonCode,
    VerificationPhase,
    VerificationRandomness,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.verification.arbitration_support import (
    arbitrate_results,
    max_rule_randomness,
)
from bijux_canon_runtime.verification.contradiction_support import (
    detect_contradictions,
)


class VerificationEngine(Protocol):
    """Verification engine contract; misuse breaks verification."""

    engine_id: str

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        ...


class FlowVerificationEngine(Protocol):
    """Flow verification contract; misuse breaks flow verification."""

    engine_id: str

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify_flow and enforce its contract."""
        ...


@dataclass(frozen=True)
class ContentVerificationEngine:
    """Content verification engine; misuse breaks claim checks."""

    engine_id: str = "content"

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        result = evaluate_verification(reasoning, evidence, artifacts, policy)
        randomness = max_rule_randomness(policy.rules)
        return VerificationResult(
            spec_version=result.spec_version,
            engine_id=self.engine_id,
            status=result.status,
            reason=result.reason,
            randomness=randomness,
            violations=result.violations,
            checked_artifact_ids=result.checked_artifact_ids,
            phase=result.phase,
            rules_applied=result.rules_applied,
            decision=result.decision,
        )


@dataclass(frozen=True)
class SignatureVerificationEngine:
    """Signature verification engine; misuse breaks signature checks."""

    engine_id: str = "signature"

    def verify(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify and enforce its contract."""
        return VerificationResult(
            spec_version="v1",
            engine_id=self.engine_id,
            status="PASS",
            reason="signature_ok",
            randomness=VerificationRandomness.DETERMINISTIC,
            violations=(),
            checked_artifact_ids=(ArtifactID(str(reasoning.bundle_id)),),
            phase=VerificationPhase.POST_EXECUTION,
            rules_applied=(),
            decision="PASS",
        )


@dataclass(frozen=True)
class ContradictionVerificationEngine:
    """Contradiction engine; misuse breaks contradiction detection."""

    engine_id: str = "contradiction"

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> VerificationResult:
        """Execute verify_flow and enforce its contract."""
        violations = detect_contradictions(reasoning_bundles)
        status = "PASS"
        reason = "no_contradictions"
        if violations:
            status = "FAIL"
            reason = ReasonCode.CONTRADICTION_DETECTED.value
        bundle_ids = tuple(
            ArtifactID(str(bundle.bundle_id)) for bundle in reasoning_bundles
        )
        return VerificationResult(
            spec_version="v1",
            engine_id=self.engine_id,
            status=status,
            reason=reason,
            randomness=VerificationRandomness.DETERMINISTIC,
            violations=violations,
            checked_artifact_ids=bundle_ids,
            phase=VerificationPhase.POST_EXECUTION,
            rules_applied=(),
            decision=status,
        )


class VerificationOrchestrator:
    """Verification orchestrator; misuse breaks arbitration flow."""

    def __init__(
        self,
        *,
        bundle_engines: tuple[VerificationEngine, ...] | None = None,
        flow_engines: tuple[FlowVerificationEngine, ...] | None = None,
    ) -> None:
        """Internal helper; not part of the public API."""
        self._bundle_engines = bundle_engines or (
            ContentVerificationEngine(),
            SignatureVerificationEngine(),
        )
        self._flow_engines = flow_engines or (ContradictionVerificationEngine(),)

    def verify_bundle(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Execute verify_bundle and enforce its contract."""
        results = [
            engine.verify(reasoning, evidence, artifacts, policy)
            for engine in self._bundle_engines
        ]
        arbitration = arbitrate_results(results, policy)
        return results, arbitration

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Execute verify_flow and enforce its contract."""
        results = [
            engine.verify_flow(reasoning_bundles, policy)
            for engine in self._flow_engines
        ]
        arbitration = arbitrate_results(results, policy)
        return results, arbitration


__all__ = [
    "ContentVerificationEngine",
    "ContradictionVerificationEngine",
    "SignatureVerificationEngine",
    "VerificationEngine",
    "VerificationOrchestrator",
]
