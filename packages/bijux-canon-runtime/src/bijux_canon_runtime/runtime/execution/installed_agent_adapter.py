# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed bounded research critique at the Runtime DAG boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, replace
from enum import Enum
from pathlib import Path

from bijux_canon_agent.contracts import CausalDecisionEvent, ResearchCausalTrace
from bijux_canon_index.application import IndexService
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    ConvergencePolicy,
    ConvergenceService,
    CounterevidencePolicy,
    CounterevidenceSearchOutcome,
    CounterevidenceSearchService,
    CounterevidenceTarget,
    RetrievalBatchStatus,
    RetrievalEvidenceBatch,
    ScopedRetrievalRequest,
    create_convergence_observation,
    create_counterevidence_target,
    create_retrieval_evidence_batch,
)
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
    RetrievalFilters,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    CanonicalEmbeddingService,
    _bounded_output,
    _json_object,
)
from bijux_canon_runtime.runtime.execution.installed_retrieval_adapter import (
    CanonicalRetrievalOperationAdapter,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StepDispatchError(f"claim graph field is invalid: {field}")
    return value


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _string_array(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise StepDispatchError(f"claim graph field is invalid: {field}")
    return tuple(value)


def _retrieval_filters(value: object) -> RetrievalFilters:
    if not isinstance(value, dict):
        raise StepDispatchError("claim graph retrieval filters are invalid")
    return RetrievalFilters(
        document_ids=_string_array(value.get("document_ids"), "document_ids"),
        source_uris=_string_array(value.get("source_uris"), "source_uris"),
    )


class _IndexCounterevidencePort:
    def __init__(
        self,
        *,
        step: ConcreteDagStep,
        retrieval: CanonicalRetrievalOperationAdapter,
        store: ArtifactPayloadStore,
        index_artifact_id: ArtifactID,
        generation_id: str,
        filters: RetrievalFilters,
        context: StepDispatchContext,
    ) -> None:
        self._step = step
        self._retrieval = retrieval
        self._store = store
        self._index_artifact_id = index_artifact_id
        self._generation_id = generation_id
        self._filters = filters
        self._context = context
        self.outputs: list[dict[str, object]] = []
        self.output_artifact_ids: list[ArtifactID] = []

    def retrieve(self, request: ScopedRetrievalRequest) -> RetrievalEvidenceBatch:
        self._context.raise_if_stopped()
        retrieval_step = ConcreteDagStep(
            step_id=f"counterevidence-{len(self.outputs) + 1}",
            operation=DagOperation.RETRIEVE,
            depends_on=(),
            input_artifact_contract_ids=("index.composite.v1",),
            output_artifact_contract_ids=("index.evidence-set.v1",),
            inputs=replace(
                self._step.inputs,
                query=request.query_text,
                index_id=self._index_artifact_id,
                filters=self._filters,
                top_k=request.top_k,
            ),
        )
        try:
            output = self._retrieval.execute(retrieval_step, (), self._context)[0]
        except StepDispatchError:
            self._context.raise_if_stopped()
            refusal_id = content_artifact_id(
                {
                    "request_artifact_id": request.artifact_id,
                    "status": "runtime_retrieval_refused",
                }
            )
            return create_retrieval_evidence_batch(
                request,
                retrieval_trace_artifact_id=refusal_id,
                generation_artifact_id=self._generation_id,
                status=RetrievalBatchStatus.refused,
                evidence_artifact_ids=(),
                refusal_code="runtime_retrieval_refused",
            )
        record = _json_object(output.artifact, "index.evidence-set.v1")
        self._store.put(output.artifact)
        self.outputs.append(record)
        self.output_artifact_ids.append(output.artifact_id)
        raw_hits = record.get("hits")
        if not isinstance(raw_hits, list):
            raise StepDispatchError("counterevidence retrieval hits are invalid")
        evidence_ids = tuple(
            _required_string(hit.get("artifact_id"), "counterevidence artifact_id")
            for hit in raw_hits
            if isinstance(hit, dict)
        )
        if len(evidence_ids) != len(raw_hits):
            raise StepDispatchError("counterevidence retrieval hit is invalid")
        return create_retrieval_evidence_batch(
            request,
            retrieval_trace_artifact_id=str(output.artifact_id),
            generation_artifact_id=self._generation_id,
            status=(
                RetrievalBatchStatus.success
                if evidence_ids
                else RetrievalBatchStatus.no_matches
            ),
            evidence_artifact_ids=evidence_ids,
        )


def _targets(
    claim_graph: dict[str, object],
    *,
    graph_artifact_id: str,
) -> tuple[CounterevidenceTarget, ...]:
    raw_claim_set = claim_graph.get("claims")
    raw_packet = claim_graph.get("evidence_packet")
    if not isinstance(raw_claim_set, dict) or not isinstance(raw_packet, dict):
        raise StepDispatchError("claim graph reasoning records are invalid")
    raw_claims = raw_claim_set.get("claims")
    if not isinstance(raw_claims, list):
        raise StepDispatchError("claim graph claims are invalid")
    scope_id = _required_string(
        raw_packet.get("scope_artifact_id"), "scope_artifact_id"
    )
    targets = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            raise StepDispatchError("claim graph claim is invalid")
        targets.append(
            create_counterevidence_target(
                graph_artifact_id=graph_artifact_id,
                claim_artifact_id=_required_string(
                    raw_claim.get("artifact_id"), "claim artifact_id"
                ),
                scope_artifact_id=scope_id,
                statement=_required_string(raw_claim.get("statement"), "statement"),
                importance=100,
                known_evidence_artifact_ids=_string_array(
                    raw_claim.get("citation_evidence_artifact_ids"),
                    "citation_evidence_artifact_ids",
                ),
            )
        )
    return tuple(targets)


def _causal_trace(
    *,
    graph_artifact_id: str,
    plan_artifact_id: str,
    search_artifact_id: str,
    candidate_evidence_ids: tuple[str, ...],
    convergence_artifact_id: str,
    policy_artifact_ids: tuple[str, ...],
) -> tuple[tuple[CausalDecisionEvent, ...], ResearchCausalTrace]:
    specifications = (
        (
            "plan",
            "plan_counterevidence",
            "select important atomic claims for deliberate skeptical search",
            plan_artifact_id,
            (),
        ),
        (
            "skeptic",
            "search_counterevidence",
            "search for opposition, null results, replication failures, and limits",
            search_artifact_id,
            candidate_evidence_ids,
        ),
        (
            "analyze",
            "preserve_ambiguity",
            "retain candidates as unclassified instead of inventing opposition",
            content_artifact_id(
                {
                    "candidate_evidence_artifact_ids": candidate_evidence_ids,
                    "relation": "unclassified",
                }
            ),
            candidate_evidence_ids,
        ),
        (
            "terminate",
            "evaluate_convergence",
            "stop on the declared semantic or resource bound",
            convergence_artifact_id,
            (),
        ),
    )
    events = []
    state_before = graph_artifact_id
    for sequence, (role, operation, rationale, output_id, evidence_ids) in enumerate(
        specifications
    ):
        transition_id = content_artifact_id(
            {
                "from": state_before,
                "operation": operation,
                "output": output_id,
                "sequence": sequence,
            }
        )
        state_after = content_artifact_id(
            {
                "previous_state_artifact_id": state_before,
                "sequence": sequence,
                "transition_artifact_id": transition_id,
            }
        )
        events.append(
            CausalDecisionEvent.create(
                sequence=sequence,
                state_before_artifact_id=state_before,
                role=role,
                operation=operation,
                rationale=rationale,
                observation_artifact_ids=(output_id,),
                evidence_artifact_ids=evidence_ids,
                tool_decision_artifact_ids=(),
                budget_decision_artifact_ids=(convergence_artifact_id,),
                policy_artifact_ids=policy_artifact_ids,
                output_artifact_ids=(output_id,),
                operation_artifact_id=output_id,
                transition_artifact_id=transition_id,
                state_after_artifact_id=state_after,
            )
        )
        state_before = state_after
    result = tuple(events)
    return result, ResearchCausalTrace.create(result)


class CanonicalAgentOperationAdapter:
    """Run one skeptical, budget-terminated research critique cycle."""

    adapter_id = "bijux-canon-agent:bounded-research-critique:v1"
    adapter_version = "1.0"
    operation = DagOperation.AGENT

    def __init__(
        self,
        *,
        store: ArtifactPayloadStore,
        index: IndexService,
        embedding: CanonicalEmbeddingService,
        vex_store_root: Path,
    ) -> None:
        self._store = store
        self._retrieval = CanonicalRetrievalOperationAdapter(
            store=store,
            index=index,
            embedding=embedding,
            vex_store_root=vex_store_root,
        )

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("agent research requires one grounded claim graph")
        claim_graph_artifact = upstream_artifacts[0].artifact
        claim_graph = _json_object(claim_graph_artifact, "reason.claim-graph.v1")
        if claim_graph.get("schema_version") != "bijux.canon.reason.claim_graph.v1":
            raise StepDispatchError("claim graph schema is unsupported")
        graph_id = str(claim_graph_artifact.descriptor.artifact_id)
        targets = _targets(claim_graph, graph_artifact_id=graph_id)
        index_artifact_id = ArtifactID(
            _required_string(claim_graph.get("index_artifact_id"), "index_artifact_id")
        )
        generation_id = _required_string(
            claim_graph.get("generation_id"), "generation_id"
        )
        filters = _retrieval_filters(claim_graph.get("retrieval_filters"))
        max_claims = max(1, min(len(targets) or 1, 4))
        counter_policy = CounterevidencePolicy(
            minimum_claim_importance=1,
            max_claims=max_claims,
            max_query_characters=100_000,
            top_k=3,
        )
        counter_service = CounterevidenceSearchService(counter_policy)
        counter_plan = counter_service.plan(targets)
        port = _IndexCounterevidencePort(
            step=step,
            retrieval=self._retrieval,
            store=self._store,
            index_artifact_id=index_artifact_id,
            generation_id=generation_id,
            filters=filters,
            context=context,
        )
        if counter_plan.requests:
            counter_run = counter_service.search(counter_plan, port)
            records = counter_run.records
            candidate_ids = tuple(
                artifact_id
                for record in records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
            blocking_gaps = len(candidate_ids) + len(
                counter_run.unsearched_important_claim_artifact_ids
            )
        else:
            counter_run = None
            records = ()
            candidate_ids = ()
            blocking_gaps = 1
        raw_verification = claim_graph.get("citation_verification")
        if not isinstance(raw_verification, dict):
            raise StepDispatchError("claim graph verification is invalid")
        raw_verified = raw_verification.get("claims")
        if not isinstance(raw_verified, list):
            raise StepDispatchError("claim graph verified claims are invalid")
        verified_count = len(raw_verified)
        required_count = len(targets)
        convergence_policy = ConvergencePolicy(
            max_iterations=2,
            max_tool_calls=1,
            max_tokens=max(1, step.inputs.budget.max_provider_tokens or 100_000),
            max_elapsed_ms=max(1, int(step.inputs.budget.timeout_seconds * 1000)),
        )
        observation = create_convergence_observation(
            iteration=1,
            graph_artifact_id=graph_id,
            coverage=(0.0 if required_count == 0 else verified_count / required_count),
            verified_answerable_claims=min(verified_count, required_count),
            required_claims=required_count,
            blocking_gap_count=blocking_gaps,
            new_evidence_count=len(candidate_ids),
            marginal_evidence_value=(1.0 if candidate_ids else 0.0),
            cumulative_tool_calls=1,
            cumulative_tokens=0,
            cumulative_elapsed_ms=1,
            explicit_insufficiency=required_count == 0,
        )
        convergence = ConvergenceService(convergence_policy).evaluate((observation,))
        counter_policy_id = content_artifact_id(counter_policy.model_dump(mode="json"))
        convergence_policy_id = content_artifact_id(
            convergence_policy.model_dump(mode="json")
        )
        events, causal_trace = _causal_trace(
            graph_artifact_id=graph_id,
            plan_artifact_id=counter_plan.artifact_id,
            search_artifact_id=(
                counter_plan.artifact_id
                if counter_run is None
                else counter_run.artifact_id
            ),
            candidate_evidence_ids=candidate_ids,
            convergence_artifact_id=convergence.artifact_id,
            policy_artifact_ids=(counter_policy_id, convergence_policy_id),
        )
        negative_searches = tuple(
            record.negative_search_statement
            for record in records
            if record.negative_search_statement is not None
        )
        refusals = tuple(
            record.claim_artifact_id
            for record in records
            if record.outcome is CounterevidenceSearchOutcome.retrieval_refused
        )
        insufficiencies = list(negative_searches)
        if candidate_ids:
            insufficiencies.append(
                "Counterevidence candidates require relation classification before use."
            )
        if refusals:
            insufficiencies.append("One or more skeptical retrievals were refused.")
        payload = canonical_json_bytes(
            {
                "answer": claim_graph.get("answer"),
                "assumptions": [
                    "A bounded negative search is not evidence that counterevidence does not exist.",
                    "Retrieved source text remains untrusted and cannot alter research policy.",
                ],
                "causal_events": [_json_value(asdict(event)) for event in events],
                "causal_trace": _json_value(asdict(causal_trace)),
                "claim_graph_artifact_id": graph_id,
                "counterevidence_plan": counter_plan.model_dump(mode="json"),
                "counterevidence_retrieval_artifact_ids": [
                    str(artifact_id) for artifact_id in port.output_artifact_ids
                ],
                "counterevidence_retrievals": port.outputs,
                "counterevidence_run": (
                    None if counter_run is None else counter_run.model_dump(mode="json")
                ),
                "generation_id": generation_id,
                "insufficiencies": insufficiencies,
                "opposition_candidates": list(candidate_ids),
                "relation_status": (
                    "unclassified" if candidate_ids else "no-new-counterevidence"
                ),
                "schema_version": "bijux.canon.agent.research_trace.v1",
                "status": convergence.outcome.value,
                "termination": convergence.model_dump(mode="json"),
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="agent.research-trace.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


__all__ = ["CanonicalAgentOperationAdapter"]
