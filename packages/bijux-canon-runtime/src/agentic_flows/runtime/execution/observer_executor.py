# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/execution/observer_executor.py."""

from __future__ import annotations

from agentic_flows.core.errors import ExecutionFailure
from agentic_flows.runtime.context import ExecutionContext
from agentic_flows.runtime.execution.step_executor import ExecutionOutcome
from agentic_flows.runtime.verification_engine import VerificationOrchestrator
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan


class ObserverExecutor:
    """Observer executor; misuse breaks observer semantics."""

    def execute(
        self, plan: ExecutionPlan, context: ExecutionContext
    ) -> ExecutionOutcome:
        """Execute execute and enforce its contract."""
        if context.observed_run is None:
            raise ExecutionFailure("observed_run is required for observer mode")
        if context.verification_policy is None:
            raise ExecutionFailure("verification_policy is required for observer mode")
        observed = context.observed_run
        orchestrator = VerificationOrchestrator()
        flow_results, flow_arbitration = orchestrator.verify_flow(
            observed.reasoning_bundles, context.verification_policy
        )
        return ExecutionOutcome(
            trace=observed.trace,
            artifacts=observed.artifacts,
            evidence=observed.evidence,
            reasoning_bundles=observed.reasoning_bundles,
            verification_results=flow_results,
            verification_arbitrations=[flow_arbitration],
        )


__all__ = ["ObserverExecutor"]
