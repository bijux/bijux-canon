# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministically expand normalized v2 requests into concrete typed DAGs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json

from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    ConcreteStepInputs,
    DagOperation,
    ExecutionProfile,
    RuntimeOperationRequest,
    RuntimeRequestOperation,
    RuntimeRequestPlan,
)


@dataclass(frozen=True, slots=True)
class _StepSpec:
    step_id: str
    operation: DagOperation
    depends_on: tuple[str, ...]
    input_contracts: tuple[str, ...]
    output_contracts: tuple[str, ...]


class RuntimeRequestPlanner:
    """Create operation-specific DAGs without dropping normalized inputs."""

    def plan(self, request: RuntimeOperationRequest) -> RuntimeRequestPlan:
        """Expand one validated request and bind every concrete input by hash."""
        specs = self._specs(request)
        if request.budget.max_steps is not None and (
            len(specs) > request.budget.max_steps
        ):
            raise ValueError("request plan exceeds the configured step budget")
        steps = tuple(
            ConcreteDagStep(
                step_id=spec.step_id,
                operation=spec.operation,
                depends_on=spec.depends_on,
                input_artifact_contract_ids=spec.input_contracts,
                output_artifact_contract_ids=spec.output_contracts,
                inputs=self._inputs_for(spec.operation, request),
            )
            for spec in specs
        )
        step_ids = {step.step_id for step in steps}
        depended_on = {dependency for step in steps for dependency in step.depends_on}
        entry_ids = tuple(step.step_id for step in steps if not step.depends_on)
        terminal_ids = tuple(
            step.step_id for step in steps if step.step_id not in depended_on
        )
        request_hash = self._hash_record(asdict(request))
        plan_payload = {
            "entry_step_ids": list(entry_ids),
            "request_id": str(request.request_id),
            "request_operation": request.operation.value,
            "request_sha256": request_hash,
            "schema_version": "bijux.runtime.request-plan.v2",
            "steps": [self._step_record(step) for step in steps],
            "terminal_step_ids": list(terminal_ids),
        }
        plan_hash = self._hash_record(plan_payload)
        plan = RuntimeRequestPlan(
            schema_version="bijux.runtime.request-plan.v2",
            request_id=request.request_id,
            request_operation=request.operation,
            request_sha256=request_hash,
            plan_sha256=plan_hash,
            entry_step_ids=entry_ids,
            terminal_step_ids=terminal_ids,
            steps=steps,
        )
        self._validate_plan(plan, step_ids)
        return plan

    @staticmethod
    def _specs(request: RuntimeOperationRequest) -> tuple[_StepSpec, ...]:
        lexical_only = request.execution_profile is ExecutionProfile.OFFLINE_LEXICAL
        ingest = _StepSpec(
            "ingest",
            DagOperation.INGEST,
            (),
            ("ingest.source-selection.v1",),
            ("ingest.source-documents.v1", "ingest.source-archive.v1"),
        )
        snapshot = _StepSpec(
            "snapshot",
            DagOperation.SNAPSHOT,
            ("ingest",),
            ("ingest.source-documents.v1", "ingest.source-archive.v1"),
            ("ingest.corpus-snapshot.v1",),
        )
        embed = _StepSpec(
            "embed",
            DagOperation.EMBED,
            (),
            ("ingest.corpus-snapshot.v1",),
            ("index.embedding-matrix.v1",),
        )
        lexical = _StepSpec(
            "lexical_index",
            DagOperation.LEXICAL_INDEX,
            (),
            ("ingest.corpus-snapshot.v1",),
            ("index.lexical.v1",),
        )
        dense = _StepSpec(
            "dense_index",
            DagOperation.DENSE_INDEX,
            ("embed", "lexical_index"),
            ("index.embedding-matrix.v1", "index.lexical.v1"),
            ("index.composite.v1",),
        )
        index_contract = "index.lexical.v1" if lexical_only else "index.composite.v1"
        retrieve_from_existing = _StepSpec(
            "retrieve",
            DagOperation.RETRIEVE,
            (),
            (index_contract,),
            ("index.evidence-set.v1",),
        )
        retrieve_from_build = _StepSpec(
            "retrieve",
            DagOperation.RETRIEVE,
            (("lexical_index",) if lexical_only else ("dense_index",)),
            (index_contract,),
            ("index.evidence-set.v1",),
        )
        reason = _StepSpec(
            "reason",
            DagOperation.REASON,
            ("retrieve",),
            ("index.evidence-set.v1",),
            ("reason.claim-graph.v1",),
        )
        agent = _StepSpec(
            "agent",
            DagOperation.AGENT,
            ("reason",),
            ("reason.claim-graph.v1",),
            ("agent.research-trace.v1",),
        )
        verify_reason = _StepSpec(
            "verify",
            DagOperation.VERIFY,
            ("reason",),
            ("reason.claim-graph.v1",),
            ("reason.verification-receipt.v1",),
        )
        verify_agent = _StepSpec(
            "verify",
            DagOperation.VERIFY,
            ("agent",),
            ("agent.research-trace.v1",),
            ("reason.verification-receipt.v1",),
        )
        persist = _StepSpec(
            "persist",
            DagOperation.PERSIST,
            ("verify",),
            ("reason.verification-receipt.v1",),
            ("runtime.run-manifest.v1",),
        )
        publish = _StepSpec(
            "publish",
            DagOperation.PUBLISH,
            ("persist",),
            ("runtime.run-manifest.v1",),
            ("runtime.publication-receipt.v1",),
        )
        if request.operation is RuntimeRequestOperation.CORPUS_PREPARE:
            return (ingest, snapshot)
        if request.operation is RuntimeRequestOperation.INDEX_BUILD:
            return (lexical,) if lexical_only else (embed, lexical, dense)
        if request.operation is RuntimeRequestOperation.RETRIEVE:
            return (retrieve_from_existing,)
        if request.operation is RuntimeRequestOperation.ASK:
            return (
                retrieve_from_existing,
                reason,
                verify_reason,
                persist,
                publish,
            )
        if request.operation is RuntimeRequestOperation.RESEARCH:
            return (
                retrieve_from_existing,
                reason,
                agent,
                verify_agent,
                persist,
                publish,
            )
        prefix: tuple[_StepSpec, ...]
        if request.source_directory is not None:
            embed = _StepSpec(
                "embed",
                DagOperation.EMBED,
                ("snapshot",),
                embed.input_contracts,
                embed.output_contracts,
            )
            lexical = _StepSpec(
                "lexical_index",
                DagOperation.LEXICAL_INDEX,
                ("snapshot",),
                lexical.input_contracts,
                lexical.output_contracts,
            )
            prefix = (
                (ingest, snapshot, lexical)
                if lexical_only
                else (ingest, snapshot, embed, lexical, dense)
            )
        else:
            prefix = (lexical,) if lexical_only else (embed, lexical, dense)
        return (
            *prefix,
            retrieve_from_build,
            reason,
            agent,
            verify_agent,
            persist,
            publish,
        )

    @staticmethod
    def _inputs_for(
        operation: DagOperation,
        request: RuntimeOperationRequest,
    ) -> ConcreteStepInputs:
        common = ConcreteStepInputs(
            request_id=request.request_id,
            request_operation=request.operation,
            execution_profile=request.execution_profile,
            budget=request.budget,
            replay_mode=request.replay_mode,
            scope=request.scope,
            execution_configuration_sha256=(request.execution_configuration_sha256),
            replay_attempt_id=request.replay_attempt_id,
            source_attempt_id=request.replay_attempt_id,
            parent_job_id=request.parent_job_id,
        )
        if operation is DagOperation.INGEST:
            return replace(
                common,
                source_directory=request.source_directory,
                source_selection_artifact_id=(request.source_selection_artifact_id),
            )
        if operation is DagOperation.SNAPSHOT:
            return replace(
                common,
                source_directory=request.source_directory,
                corpus_id=request.corpus_id,
            )
        if operation in {
            DagOperation.EMBED,
            DagOperation.LEXICAL_INDEX,
            DagOperation.DENSE_INDEX,
        }:
            return replace(common, corpus_id=request.corpus_id)
        if operation is DagOperation.RETRIEVE:
            return replace(
                common,
                query=request.query,
                corpus_id=request.corpus_id,
                index_id=request.index_id,
                filters=request.filters,
                top_k=request.top_k,
            )
        if operation in {DagOperation.REASON, DagOperation.AGENT}:
            return replace(
                common,
                query=request.query,
                provider=request.provider,
                output_policy=request.output_policy,
            )
        return replace(
            common,
            corpus_id=request.corpus_id,
            index_id=request.index_id,
            output_policy=request.output_policy,
        )

    @staticmethod
    def _step_record(step: ConcreteDagStep) -> dict[str, object]:
        return {
            "depends_on": list(step.depends_on),
            "input_artifact_contract_ids": list(step.input_artifact_contract_ids),
            "inputs": asdict(step.inputs),
            "operation": step.operation.value,
            "output_artifact_contract_ids": list(step.output_artifact_contract_ids),
            "step_id": step.step_id,
        }

    @staticmethod
    def _hash_record(record: object) -> str:
        payload = json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _validate_plan(plan: RuntimeRequestPlan, step_ids: set[str]) -> None:
        if len(step_ids) != len(plan.steps):
            raise ValueError("request plan step identities must be unique")
        for step in plan.steps:
            if not set(step.depends_on).issubset(step_ids):
                raise ValueError("request plan dependency is unresolved")
            if step.step_id in step.depends_on:
                raise ValueError("request plan step cannot depend on itself")
            if not step.input_artifact_contract_ids:
                raise ValueError("request plan step has no input artifact contract")
            if not step.output_artifact_contract_ids:
                raise ValueError("request plan step has no output artifact contract")
            for dependency_id in step.depends_on:
                dependency = next(
                    item for item in plan.steps if item.step_id == dependency_id
                )
                if not set(dependency.output_artifact_contract_ids).intersection(
                    step.input_artifact_contract_ids
                ):
                    raise ValueError(
                        "request plan edge has no matching artifact contract"
                    )

        remaining = set(step_ids)
        resolved: set[str] = set()
        while remaining:
            ready = {
                step.step_id
                for step in plan.steps
                if step.step_id in remaining and set(step.depends_on).issubset(resolved)
            }
            if not ready:
                raise ValueError("request plan contains a dependency cycle")
            remaining.difference_update(ready)
            resolved.update(ready)


__all__ = ["RuntimeRequestPlanner"]
