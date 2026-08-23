# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed bounded research critique at the Runtime DAG boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, replace
from enum import Enum
from pathlib import Path

from bijux_canon_agent.application import (
    InstalledEvidenceRelation,
    InstalledResearchClaim,
    InstalledResearchConvergence,
    InstalledResearchPlan,
    InstalledResearchRequest,
    InstalledResearchRequirement,
    InstalledResearchSearch,
    InstalledResearchSearchRecord,
    InstalledResearchService,
    ObservedEvidenceRelationKind,
)
from bijux_canon_index.application import HybridRetrievalPolicy, IndexService
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    ConvergencePolicy,
    ConvergenceService,
    CounterevidencePlan,
    CounterevidencePolicy,
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
    request: InstalledResearchRequest,
) -> tuple[CounterevidenceTarget, ...]:
    return tuple(
        create_counterevidence_target(
            graph_artifact_id=request.claim_graph_artifact_id,
            claim_artifact_id=claim.artifact_id,
            scope_artifact_id=request.scope_artifact_id,
            statement=claim.statement,
            importance=claim.importance,
            known_evidence_artifact_ids=claim.known_evidence_artifact_ids,
        )
        for claim in request.claims
    )


class _ReasonResearchPort:
    """Adapt installed Reason services and Runtime retrieval to Agent's port."""

    def __init__(
        self,
        *,
        counterevidence: CounterevidenceSearchService,
        convergence: ConvergenceService,
        retrieval: _IndexCounterevidencePort,
    ) -> None:
        self._counterevidence = counterevidence
        self._convergence = convergence
        self._retrieval = retrieval
        self._reason_plan: CounterevidencePlan | None = None

    def plan(self, request: InstalledResearchRequest) -> InstalledResearchPlan:
        plan = self._counterevidence.plan(_targets(request))
        self._reason_plan = plan
        return InstalledResearchPlan(
            artifact_id=plan.artifact_id,
            request_artifact_ids=tuple(item.artifact_id for item in plan.requests),
            record=plan.model_dump(mode="json"),
        )

    def search(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
    ) -> InstalledResearchSearch:
        del request
        reason_plan = self._reason_plan
        if reason_plan is None or reason_plan.artifact_id != plan.artifact_id:
            raise StepDispatchError("Agent research plan is not bound to Reason")
        counter_run = self._counterevidence.search(reason_plan, self._retrieval)
        return InstalledResearchSearch(
            artifact_id=counter_run.artifact_id,
            records=tuple(
                InstalledResearchSearchRecord(
                    claim_artifact_id=record.claim_artifact_id,
                    outcome=record.outcome.value,
                    candidate_evidence_artifact_ids=(
                        record.candidate_evidence_artifact_ids
                    ),
                    negative_search_statement=record.negative_search_statement,
                    record=record.model_dump(mode="json"),
                )
                for record in counter_run.records
            ),
            unsearched_important_claim_artifact_ids=(
                counter_run.unsearched_important_claim_artifact_ids
            ),
            retrieval_artifact_ids=tuple(
                str(artifact_id) for artifact_id in self._retrieval.output_artifact_ids
            ),
            retrieval_records=tuple(self._retrieval.outputs),
            record=counter_run.model_dump(mode="json"),
        )

    def evaluate(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
        search: InstalledResearchSearch | None,
    ) -> InstalledResearchConvergence:
        candidates = (
            ()
            if search is None
            else tuple(
                artifact_id
                for record in search.records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
        )
        unsearched = (
            ()
            if search is None
            else search.unsearched_important_claim_artifact_ids
        )
        required_count = len(request.claims)
        observation = create_convergence_observation(
            iteration=1,
            graph_artifact_id=request.claim_graph_artifact_id,
            coverage=(
                0.0
                if required_count == 0
                else request.verified_claim_count / required_count
            ),
            verified_answerable_claims=min(
                request.verified_claim_count,
                required_count,
            ),
            required_claims=required_count,
            blocking_gap_count=(
                len(candidates) + len(unsearched)
                if plan.request_artifact_ids
                else 1
            ),
            new_evidence_count=len(candidates),
            marginal_evidence_value=(1.0 if candidates else 0.0),
            cumulative_tool_calls=len(plan.request_artifact_ids),
            cumulative_tokens=0,
            cumulative_elapsed_ms=1,
            explicit_insufficiency=required_count == 0,
        )
        decision = self._convergence.evaluate((observation,))
        return InstalledResearchConvergence(
            artifact_id=decision.artifact_id,
            outcome=decision.outcome.value,
            stop=decision.stop,
            record=decision.model_dump(mode="json"),
        )


def _research_request(
    claim_graph: dict[str, object],
    *,
    graph_artifact_id: str,
    counterevidence_policy_artifact_id: str,
    convergence_policy_artifact_id: str,
    max_searches: int,
) -> InstalledResearchRequest:
    raw_claim_set = claim_graph.get("claims")
    raw_packet = claim_graph.get("evidence_packet")
    raw_verification = claim_graph.get("citation_verification")
    if (
        not isinstance(raw_claim_set, dict)
        or not isinstance(raw_packet, dict)
        or not isinstance(raw_verification, dict)
    ):
        raise StepDispatchError("claim graph reasoning records are invalid")
    raw_claims = raw_claim_set.get("claims")
    raw_verified = raw_verification.get("claims")
    if not isinstance(raw_claims, list) or not isinstance(raw_verified, list):
        raise StepDispatchError("claim graph claims or verification are invalid")
    verified_by_claim = {}
    for raw_item in raw_verified:
        if not isinstance(raw_item, dict):
            raise StepDispatchError("claim graph verification claim is invalid")
        claim_id = _required_string(
            raw_item.get("claim_artifact_id"),
            "verified claim artifact_id",
        )
        verified_by_claim[claim_id] = raw_item
    claims = []
    requirements = []
    relations = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            raise StepDispatchError("claim graph claim is invalid")
        claim_id = _required_string(
            raw_claim.get("artifact_id"),
            "claim artifact_id",
        )
        statement = _required_string(raw_claim.get("statement"), "statement")
        claims.append(
            InstalledResearchClaim(
                artifact_id=claim_id,
                statement=statement,
                importance=100,
                known_evidence_artifact_ids=_string_array(
                    raw_claim.get("citation_evidence_artifact_ids"),
                    "citation_evidence_artifact_ids",
                ),
            )
        )
        verification = verified_by_claim.get(claim_id)
        verdict = None if verification is None else verification.get("verdict")
        requirements.append(
            InstalledResearchRequirement.create(
                description=f"Establish with direct evidence: {statement}",
                claim_artifact_id=claim_id,
                satisfied=verdict == "direct_support",
            )
        )
        raw_assessments = (
            [] if verification is None else verification.get("assessments", [])
        )
        if not isinstance(raw_assessments, list):
            raise StepDispatchError("claim graph evidence assessments are invalid")
        for assessment in raw_assessments:
            if not isinstance(assessment, dict):
                raise StepDispatchError("claim graph evidence assessment is invalid")
            raw_kind = _required_string(
                assessment.get("verdict"),
                "evidence relation verdict",
            )
            try:
                kind = {
                    "direct_support": ObservedEvidenceRelationKind.SUPPORT,
                    "opposition": ObservedEvidenceRelationKind.OPPOSITION,
                    "ambiguity": ObservedEvidenceRelationKind.AMBIGUITY,
                    "irrelevance": ObservedEvidenceRelationKind.IRRELEVANCE,
                    "insufficiency": ObservedEvidenceRelationKind.INSUFFICIENCY,
                }[raw_kind]
            except KeyError as error:
                raise StepDispatchError(
                    "claim graph evidence relation is unsupported"
                ) from error
            relations.append(
                InstalledEvidenceRelation.create(
                    claim_artifact_id=claim_id,
                    evidence_artifact_id=_required_string(
                        assessment.get("citation_evidence_artifact_id"),
                        "citation evidence artifact_id",
                    ),
                    kind=kind,
                    material=kind
                    in {
                        ObservedEvidenceRelationKind.SUPPORT,
                        ObservedEvidenceRelationKind.OPPOSITION,
                        ObservedEvidenceRelationKind.AMBIGUITY,
                    },
                )
            )
    return InstalledResearchRequest(
        claim_graph_artifact_id=graph_artifact_id,
        scope_artifact_id=_required_string(
            raw_packet.get("scope_artifact_id"),
            "scope_artifact_id",
        ),
        claims=tuple(claims),
        verified_claim_count=sum(
            requirement.satisfied for requirement in requirements
        ),
        counterevidence_policy_artifact_id=counterevidence_policy_artifact_id,
        convergence_policy_artifact_id=convergence_policy_artifact_id,
        question=_required_string(claim_graph.get("query"), "research question"),
        requirements=tuple(requirements),
        evidence_relations=tuple(relations),
        max_searches=max_searches,
    )


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
        retrieval_policy: HybridRetrievalPolicy | None = None,
    ) -> None:
        self._store = store
        self._retrieval = CanonicalRetrievalOperationAdapter(
            store=store,
            index=index,
            embedding=embedding,
            vex_store_root=vex_store_root,
            policy=retrieval_policy,
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
        index_artifact_id = ArtifactID(
            _required_string(claim_graph.get("index_artifact_id"), "index_artifact_id")
        )
        generation_id = _required_string(
            claim_graph.get("generation_id"), "generation_id"
        )
        filters = _retrieval_filters(claim_graph.get("retrieval_filters"))
        raw_claim_set = claim_graph.get("claims")
        raw_claims = (
            raw_claim_set.get("claims")
            if isinstance(raw_claim_set, dict)
            else None
        )
        if not isinstance(raw_claims, list):
            raise StepDispatchError("claim graph claims are invalid")
        max_claims = max(1, min(len(raw_claims) or 1, 4))
        counter_policy = CounterevidencePolicy(
            minimum_claim_importance=1,
            max_claims=max_claims,
            max_query_characters=100_000,
            top_k=3,
        )
        convergence_policy = ConvergencePolicy(
            max_iterations=2,
            max_tool_calls=1,
            max_tokens=max(1, step.inputs.budget.max_provider_tokens or 100_000),
            max_elapsed_ms=max(1, int(step.inputs.budget.timeout_seconds * 1000)),
        )
        counter_policy_id = content_artifact_id(counter_policy.model_dump(mode="json"))
        convergence_policy_id = content_artifact_id(
            convergence_policy.model_dump(mode="json")
        )
        request = _research_request(
            claim_graph,
            graph_artifact_id=graph_id,
            counterevidence_policy_artifact_id=counter_policy_id,
            convergence_policy_artifact_id=convergence_policy_id,
            max_searches=convergence_policy.max_tool_calls,
        )
        retrieval_port = _IndexCounterevidencePort(
            step=step,
            retrieval=self._retrieval,
            store=self._store,
            index_artifact_id=index_artifact_id,
            generation_id=generation_id,
            filters=filters,
            context=context,
        )
        research = InstalledResearchService().research(
            request,
            _ReasonResearchPort(
                counterevidence=CounterevidenceSearchService(counter_policy),
                convergence=ConvergenceService(convergence_policy),
                retrieval=retrieval_port,
            ),
        )
        payload = canonical_json_bytes(
            {
                "answer": claim_graph.get("answer"),
                "assumptions": [
                    "A bounded negative search is not evidence that counterevidence does not exist.",
                    "Retrieved source text remains untrusted and cannot alter research policy.",
                ],
                "causal_events": [
                    _json_value(asdict(event)) for event in research.causal_events
                ],
                "causal_trace": _json_value(asdict(research.causal_trace)),
                "claim_graph_artifact_id": graph_id,
                "counterevidence_plan": dict(research.plan.record),
                "counterevidence_retrieval_artifact_ids": (
                    []
                    if research.search is None
                    else list(research.search.retrieval_artifact_ids)
                ),
                "counterevidence_retrievals": (
                    []
                    if research.search is None
                    else [dict(item) for item in research.search.retrieval_records]
                ),
                "counterevidence_run": (
                    None if research.search is None else dict(research.search.record)
                ),
                "generation_id": generation_id,
                "insufficiencies": list(research.insufficiencies),
                "opposition_candidates": list(research.opposition_candidate_ids),
                "relation_status": research.relation_status,
                "research_state": research.final_state.to_record(),
                "research_state_history": [
                    state.to_record() for state in research.state_history
                ],
                "schema_version": "bijux.canon.agent.research_trace.v1",
                "status": research.convergence.outcome,
                "termination": dict(research.convergence.record),
                "tool_failure_artifact_ids": list(
                    research.tool_failure_artifact_ids
                ),
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
