# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for runtime/execution/reasoning_executor.py."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

import bijux_rar

from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.spec.model.artifact.artifact import Artifact
from bijux_canon_runtime.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.spec.model.execution.resolved_step import ResolvedStep
from bijux_canon_runtime.spec.model.reasoning_bundle import ReasoningBundle


class ReasoningExecutor:
    """Behavioral contract for ReasoningExecutor."""

    def execute(self, step: ResolvedStep, context: ExecutionContext) -> ReasoningBundle:
        """Execute execute and enforce its contract."""
        if not hasattr(bijux_rar, "reason"):
            raise RuntimeError("bijux_rar.reason is required for reasoning")

        agent_outputs = list(context.artifacts_for_step(step.step_index))
        retrieved_evidence = list(context.evidence_for_step(step.step_index))
        seed = self._deterministic_seed(agent_outputs, retrieved_evidence)
        bundle = bijux_rar.reason(
            agent_outputs=agent_outputs,
            evidence=retrieved_evidence,
            seed=seed,
        )
        if not isinstance(bundle, ReasoningBundle):
            raise ValueError("bijux_rar.reason must return ReasoningBundle")
        return bundle

    @staticmethod
    def bundle_hash(bundle: ReasoningBundle) -> str:
        """Execute bundle_hash and enforce its contract."""
        payload = json.dumps(
            asdict(bundle), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _deterministic_seed(
        agent_outputs: list[Artifact],
        retrieved_evidence: list[RetrievedEvidence],
    ) -> int:
        """Internal helper; not part of the public API."""
        payload = json.dumps(
            {
                "artifact_hashes": [
                    artifact.content_hash for artifact in agent_outputs
                ],
                "evidence_hashes": [
                    evidence.content_hash for evidence in retrieved_evidence
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)
