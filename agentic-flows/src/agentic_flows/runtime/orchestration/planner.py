# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/orchestration/planner.py."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    bijux_agent_version = version("bijux-agent")
except PackageNotFoundError:
    bijux_agent_version = "0.0.0"

try:
    bijux_cli_version = version("bijux-cli")
except PackageNotFoundError:
    bijux_cli_version = "0.0.0"

from agentic_flows.runtime.observability.capture.environment import (
    compute_environment_fingerprint,
)
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from agentic_flows.spec.contracts.execution_plan_contract import (
    validate as validate_execution_plan,
)
from agentic_flows.spec.contracts.flow_contract import (
    validate as validate_flow_manifest,
)
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.ontology import StepType
from agentic_flows.spec.ontology.ids import (
    AgentID,
    EnvironmentFingerprint,
    FlowID,
    InputsFingerprint,
    PlanHash,
    ResolverID,
    VersionID,
)


class ExecutionPlanner:
    """Behavioral contract for ExecutionPlanner."""

    resolver_id: ResolverID = ResolverID("agentic-flows:v0")
    _bijux_cli_version: str = bijux_cli_version
    _bijux_agent_version: str = bijux_agent_version

    def resolve(self, manifest: FlowManifest) -> ExecutionPlan:
        """Execute resolve and enforce its contract."""
        validate_flow_manifest(manifest)
        ordered_agents = self._toposort_agents(manifest)
        dependencies = self._parse_dependencies(manifest)
        steps = []
        for index, agent_id in enumerate(ordered_agents):
            declared = sorted(dependencies.get(agent_id, []))
            inputs_fingerprint = InputsFingerprint(
                fingerprint_inputs(
                    {
                        "agent_id": agent_id,
                        "declared_dependencies": declared,
                        "retrieval_contracts": list(manifest.retrieval_contracts),
                        "verification_gates": list(manifest.verification_gates),
                    }
                )
            )
            steps.append(
                ResolvedStep(
                    spec_version="v1",
                    step_index=index,
                    step_type=StepType.AGENT,
                    determinism_level=manifest.determinism_level,
                    agent_id=AgentID(agent_id),
                    inputs_fingerprint=inputs_fingerprint,
                    declared_dependencies=tuple(AgentID(dep) for dep in declared),
                    expected_artifacts=(),
                    agent_invocation=AgentInvocation(
                        spec_version="v1",
                        agent_id=AgentID(agent_id),
                        agent_version=VersionID(self._bijux_agent_version),
                        inputs_fingerprint=inputs_fingerprint,
                        declared_outputs=(),
                        execution_mode="seeded",
                    ),
                    retrieval_request=None,
                    declared_entropy_budget=manifest.entropy_budget,
                    allowed_variance_class=manifest.allowed_variance_class,
                    nondeterminism_intent=manifest.nondeterminism_intent,
                )
            )
        plan_hash = self._plan_hash(manifest, steps, dependencies)
        plan = ExecutionSteps(
            spec_version="v1",
            flow_id=FlowID(manifest.flow_id),
            tenant_id=manifest.tenant_id,
            flow_state=manifest.flow_state,
            determinism_level=manifest.determinism_level,
            replay_mode=manifest.replay_mode,
            replay_acceptability=manifest.replay_acceptability,
            entropy_budget=manifest.entropy_budget,
            allowed_variance_class=manifest.allowed_variance_class,
            nondeterminism_intent=manifest.nondeterminism_intent,
            replay_envelope=manifest.replay_envelope,
            dataset=manifest.dataset,
            allow_deprecated_datasets=manifest.allow_deprecated_datasets,
            steps=tuple(steps),
            environment_fingerprint=EnvironmentFingerprint(
                compute_environment_fingerprint()
            ),
            plan_hash=plan_hash,
            resolution_metadata=(
                ("resolver_id", self.resolver_id),
                ("bijux_cli_version", self._bijux_cli_version),
            ),
        )
        resolved = ExecutionPlan(
            spec_version="v1",
            manifest=manifest,
            plan=plan,
        )
        validate_execution_plan(resolved)
        return resolved

    def _toposort_agents(self, manifest: FlowManifest) -> list[str]:
        """Deterministic topological sort using lexical tie-breaking for stability."""
        dependencies = self._parse_dependencies(manifest)
        agents = set(manifest.agents)
        indegree = dict.fromkeys(agents, 0)
        forward = {agent: [] for agent in agents}

        for agent, deps in dependencies.items():
            for dep in deps:
                forward[dep].append(agent)
                indegree[agent] += 1

        ready = sorted([agent for agent, degree in indegree.items() if degree == 0])
        ordered = []
        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for downstream in sorted(forward[current]):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    ready.append(downstream)
                    ready.sort()

        if len(ordered) != len(agents):
            raise ValueError("dependencies contain a cycle or reference unknown agents")
        return ordered

    def _parse_dependencies(self, manifest: FlowManifest) -> dict[str, list[str]]:
        """Internal helper; not part of the public API."""
        agents = set(manifest.agents)
        mapping: dict[str, list[str]] = {agent: [] for agent in agents}
        for entry in manifest.dependencies:
            parts = [part.strip() for part in entry.split(":")]
            if len(parts) != 2 or not all(parts):
                raise ValueError("dependencies must use 'agent:dependency' format")
            agent_id, dependency_id = parts
            if agent_id not in agents or dependency_id not in agents:
                raise ValueError("dependencies must reference known agents")
            mapping[agent_id].append(dependency_id)
        return mapping

    def _plan_hash(
        self,
        manifest: FlowManifest,
        steps: list[ResolvedStep],
        dependencies: dict[str, list[str]],
    ) -> PlanHash:
        """Internal helper; not part of the public API."""
        payload = {
            "flow_id": manifest.flow_id,
            "tenant_id": manifest.tenant_id,
            "flow_state": manifest.flow_state,
            "determinism_level": manifest.determinism_level,
            "replay_mode": manifest.replay_mode,
            "replay_acceptability": manifest.replay_acceptability,
            "entropy_budget": {
                "allowed_sources": list(manifest.entropy_budget.allowed_sources),
                "min_magnitude": manifest.entropy_budget.min_magnitude,
                "max_magnitude": manifest.entropy_budget.max_magnitude,
                "exhaustion_action": manifest.entropy_budget.exhaustion_action,
                "per_source": [
                    {
                        "source": entry.source,
                        "min_magnitude": entry.min_magnitude,
                        "max_magnitude": entry.max_magnitude,
                        "exhaustion_action": entry.exhaustion_action,
                    }
                    for entry in manifest.entropy_budget.per_source
                ],
            },
            "allowed_variance_class": manifest.allowed_variance_class,
            "nondeterminism_intent": [
                {
                    "source": intent.source,
                    "min_entropy_magnitude": intent.min_entropy_magnitude,
                    "max_entropy_magnitude": intent.max_entropy_magnitude,
                    "justification": intent.justification,
                }
                for intent in manifest.nondeterminism_intent
            ],
            "replay_envelope": {
                "min_claim_overlap": manifest.replay_envelope.min_claim_overlap,
                "max_contradiction_delta": (
                    manifest.replay_envelope.max_contradiction_delta
                ),
            },
            "dataset": {
                "dataset_id": manifest.dataset.dataset_id,
                "tenant_id": manifest.dataset.tenant_id,
                "dataset_version": manifest.dataset.dataset_version,
                "dataset_hash": manifest.dataset.dataset_hash,
                "dataset_state": manifest.dataset.dataset_state,
            },
            "allow_deprecated_datasets": manifest.allow_deprecated_datasets,
            "steps": [
                {
                    "index": step.step_index,
                    "agent_id": step.agent_id,
                    "inputs_fingerprint": step.inputs_fingerprint,
                    "declared_dependencies": list(step.declared_dependencies),
                    "step_type": step.step_type,
                    "determinism_level": step.determinism_level,
                    "declared_entropy_budget": (
                        {
                            "allowed_sources": list(
                                step.declared_entropy_budget.allowed_sources
                            ),
                            "min_magnitude": step.declared_entropy_budget.min_magnitude,
                            "max_magnitude": step.declared_entropy_budget.max_magnitude,
                            "exhaustion_action": step.declared_entropy_budget.exhaustion_action,
                            "per_source": [
                                {
                                    "source": entry.source,
                                    "min_magnitude": entry.min_magnitude,
                                    "max_magnitude": entry.max_magnitude,
                                    "exhaustion_action": entry.exhaustion_action,
                                }
                                for entry in step.declared_entropy_budget.per_source
                            ],
                        }
                        if step.declared_entropy_budget
                        else None
                    ),
                    "allowed_variance_class": step.allowed_variance_class,
                    "nondeterminism_intent": [
                        {
                            "source": intent.source,
                            "min_entropy_magnitude": intent.min_entropy_magnitude,
                            "max_entropy_magnitude": intent.max_entropy_magnitude,
                            "justification": intent.justification,
                        }
                        for intent in step.nondeterminism_intent
                    ],
                }
                for step in steps
            ],
            "dependencies": {
                agent_id: sorted(deps) for agent_id, deps in dependencies.items()
            },
        }
        return PlanHash(fingerprint_inputs(payload))
