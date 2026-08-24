# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed bounded research critique at the Runtime DAG boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, replace
from enum import Enum
from pathlib import Path

from pydantic import ValidationError

from bijux_canon_agent.application import (
    BudgetDimensions,
    CancellationSignal,
    InstalledCandidateClassification,
    InstalledEvidenceRelation,
    InstalledResearchClaim,
    InstalledResearchConvergence,
    InstalledResearchPlan,
    InstalledResearchRequest,
    InstalledResearchRequirement,
    InstalledResearchRevision,
    InstalledResearchSearch,
    InstalledResearchSearchRecord,
    InstalledResearchService,
    ObservedEvidenceRelationKind,
    TargetedSearchAttempt,
    TargetedSearchPlan,
)
from bijux_canon_index.application import HybridRetrievalPolicy, IndexService
from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    CitationVerificationReport,
    CredentialFreeSynthesis,
    EvidencePacket,
    GroundingAdmissionDecision,
    LocalGroundedAnswer,
    NormalizedClaimSet,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    AnswerVerificationStatus,
    AnswerRequirementKind,
    AnswerRequirementPlanningService,
    AnswerRequirementStatus,
    ConvergencePolicy,
    ConvergenceService,
    CounterevidencePlan,
    CounterevidencePolicy,
    CounterevidenceSearchService,
    CounterevidenceTarget,
    ResearchCandidateAdjudicationService,
    ResearchAnswerRevision,
    ResearchAnswerRevisionService,
    ResearchCandidateClassification,
    RetrievalBatchStatus,
    RetrievalEvidenceBatch,
    ScopedRetrievalRequest,
    create_convergence_observation,
    create_counterevidence_target,
    create_research_convergence_evidence,
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
from bijux_canon_runtime.runtime.execution.installed_reason_adapter import (
    citation_inputs_from_evidence_set,
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
        self.evidence: dict[str, CitationEvidence] = {}
        self.sources: dict[str, CitationSourceDescriptor] = {}

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
        candidate_evidence, sources = citation_inputs_from_evidence_set(
            record,
            retrieval_artifact_id=str(output.artifact_id),
            claim_key=request.target_artifact_id,
        )
        canonical: list[CitationEvidence] = []
        for source in sources:
            existing_source = self.sources.get(source.source_id)
            if existing_source is not None and existing_source != source:
                raise StepDispatchError("counterevidence source metadata collision")
            self.sources[source.source_id] = source
        seen_text: set[str] = set()
        for evidence in candidate_evidence:
            if evidence.exact_text_sha256 in seen_text:
                continue
            seen_text.add(evidence.exact_text_sha256)
            existing = self.evidence.get(evidence.artifact_id)
            if existing is not None and existing != evidence:
                raise StepDispatchError("counterevidence identity collision")
            self.evidence[evidence.artifact_id] = evidence
            canonical.append(evidence)
        evidence_ids = tuple(item.artifact_id for item in canonical)
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


class _RuntimeCancellationPort:
    """Project Runtime's cooperative signal into Agent's typed contract."""

    def __init__(self, context: StepDispatchContext, request_artifact_id: str) -> None:
        self._context = context
        self._request_artifact_id = request_artifact_id

    def current(self) -> CancellationSignal:
        if self._context.is_cancelled():
            return CancellationSignal.active(
                reason="runtime cancellation requested",
                request_artifact_id=self._request_artifact_id,
            )
        return CancellationSignal.inactive()


class _ReasonResearchPort:
    """Adapt installed Reason services and Runtime retrieval to Agent's port."""

    def __init__(
        self,
        *,
        counterevidence: CounterevidenceSearchService,
        convergence: ConvergenceService,
        retrieval: _IndexCounterevidencePort,
        claim_graph: dict[str, object],
        claim_graph_artifact_id: str,
    ) -> None:
        self._counterevidence = counterevidence
        self._convergence = convergence
        self._retrieval = retrieval
        self._claim_graph = claim_graph
        self._claim_graph_artifact_id = claim_graph_artifact_id
        self._reason_plan: CounterevidencePlan | None = None
        self._targeted_attempt: TargetedSearchAttempt | None = None
        self._search_count = 0
        self._search_history: list[InstalledResearchSearch] = []
        self._revision: ResearchAnswerRevision | None = None
        self._resolved_requirement_ids: set[str] = set()

    def revise(
        self,
        request: InstalledResearchRequest,
        searches: tuple[InstalledResearchSearch, ...],
    ) -> InstalledResearchRevision:
        """Re-run the installed grounded-answer pipeline over classified evidence."""

        if request.claim_graph_artifact_id != self._claim_graph_artifact_id:
            raise StepDispatchError("research revision targets another claim graph")
        raw = self._claim_graph
        try:
            prior_answer = LocalGroundedAnswer.model_validate(
                {
                    "artifact_id": raw.get("grounded_answer_artifact_id"),
                    "answer_text": raw.get("answer"),
                    "outcome": raw.get("answer_disposition"),
                    "synthesis": raw.get("synthesis"),
                    "claims": raw.get("claims"),
                    "citations": raw.get("citations"),
                    "citation_presentation": raw.get("citation_presentation"),
                    "verification": raw.get("citation_verification"),
                    "admission": raw.get("grounding_admission"),
                    "contextualized": raw.get("contextualized"),
                    "evidence_state": raw.get("evidence_state"),
                }
            )
            prior_packet = EvidencePacket.model_validate(raw.get("evidence_packet"))
            classifications = tuple(
                ResearchCandidateClassification.model_validate(item.record)
                for search in searches
                for record in search.records
                for item in record.classifications
            )
            candidate_ids = tuple(
                dict.fromkeys(
                    item.evidence_artifact_id for item in classifications
                )
            )
            candidates = tuple(
                self._retrieval.evidence[artifact_id]
                for artifact_id in candidate_ids
            )
            raw_sources = raw.get("sources")
            if not isinstance(raw_sources, list):
                raise ValueError("prior claim graph source records are invalid")
            source_by_id = {
                source.source_id: source
                for source in (
                    CitationSourceDescriptor.model_validate(item)
                    for item in raw_sources
                )
            }
            for source_id, source in self._retrieval.sources.items():
                previous = source_by_id.get(source_id)
                if previous is not None and previous != source:
                    raise ValueError("research revision source metadata collides")
                source_by_id[source_id] = source
            revision = ResearchAnswerRevisionService().revise(
                prior_claim_graph_artifact_id=self._claim_graph_artifact_id,
                prior_answer=prior_answer,
                prior_evidence_packet=prior_packet,
                classifications=classifications,
                candidate_evidence=candidates,
                sources=tuple(source_by_id.values()),
            )
        except (KeyError, ValidationError, ValueError) as error:
            raise StepDispatchError(
                "research evidence cannot produce a verified answer revision"
            ) from error
        self._revision = revision
        return InstalledResearchRevision(
            artifact_id=revision.artifact_id,
            outcome=revision.outcome.value,
            changed=revision.before_answer != revision.after_answer,
            prior_claim_artifact_ids=revision.prior_claim_artifact_ids,
            revised_claim_artifact_ids=(
                revision.revised_answer.admission.admitted_claim_artifact_ids
            ),
            resolved_classification_artifact_ids=(
                revision.resolved_classification_artifact_ids
            ),
            unresolved_classification_artifact_ids=(
                revision.unresolved_classification_artifact_ids
            ),
            before_answer=revision.before_answer,
            after_answer=revision.after_answer,
            record=revision.model_dump(mode="json"),
        )

    def plan(
        self,
        request: InstalledResearchRequest,
        targeted_search_plan: TargetedSearchPlan | None,
    ) -> InstalledResearchPlan:
        attempt = None if targeted_search_plan is None else targeted_search_plan.attempt
        if attempt is None:
            targets: tuple[CounterevidenceTarget, ...] = ()
        else:
            requirement = next(
                (
                    item
                    for item in request.requirements
                    if item.artifact_id == attempt.requirement_artifact_id
                    or (
                        attempt.source_requirement_artifact_id is not None
                        and item.source_requirement_artifact_id
                        == attempt.source_requirement_artifact_id
                    )
                ),
                None,
            )
            if requirement is None:
                raise StepDispatchError(
                    "targeted search references an unknown answer requirement"
                )
            targets = (
                create_counterevidence_target(
                    graph_artifact_id=request.claim_graph_artifact_id,
                    claim_artifact_id=attempt.requirement_artifact_id,
                    scope_artifact_id=request.scope_artifact_id,
                    statement=attempt.query_text,
                    importance=requirement.priority,
                    known_evidence_artifact_ids=requirement.evidence_artifact_ids,
                ),
            )
        plan = self._counterevidence.plan(targets)
        self._reason_plan = plan
        self._targeted_attempt = attempt
        return InstalledResearchPlan(
            artifact_id=plan.artifact_id,
            request_artifact_ids=tuple(item.artifact_id for item in plan.requests),
            record=plan.model_dump(mode="json"),
            targeted_search_plan=targeted_search_plan,
        )

    def search(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
    ) -> InstalledResearchSearch:
        reason_plan = self._reason_plan
        if reason_plan is None or reason_plan.artifact_id != plan.artifact_id:
            raise StepDispatchError("Agent research plan is not bound to Reason")
        attempt = self._targeted_attempt
        if attempt is None:
            raise StepDispatchError("Agent research search has no targeted attempt")
        counter_run = self._counterevidence.search(reason_plan, self._retrieval)
        self._search_count += 1
        requirement = next(
            (
                item
                for item in request.requirements
                if item.artifact_id == attempt.requirement_artifact_id
                or (
                    attempt.source_requirement_artifact_id is not None
                    and item.source_requirement_artifact_id
                    == attempt.source_requirement_artifact_id
                )
            ),
            None,
        )
        if requirement is None:
            raise StepDispatchError(
                "candidate requirement is absent from research input"
            )
        claims = {item.artifact_id: item.statement for item in request.claims}
        target_claim_ids: tuple[str | None, ...] = (
            tuple(attempt.target_claim_artifact_ids)
            if attempt.target_claim_artifact_ids
            else (None,)
        )
        classifications: list[InstalledCandidateClassification] = []
        adjudication_records: list[dict[str, object]] = []
        candidate_ids = tuple(
            artifact_id
            for record in counter_run.records
            for artifact_id in record.candidate_evidence_artifact_ids
        )
        candidate_evidence = tuple(
            self._retrieval.evidence[artifact_id] for artifact_id in candidate_ids
        )
        adjudicator = ResearchCandidateAdjudicationService()
        for claim_id in target_claim_ids:
            if claim_id is not None and claim_id not in claims:
                raise StepDispatchError("candidate claim is absent from research input")
            report = adjudicator.classify(
                requirement_artifact_id=attempt.requirement_artifact_id,
                requirement_kind=requirement.kind,
                target_statement=(
                    requirement.description if claim_id is None else claims[claim_id]
                ),
                claim_artifact_id=claim_id,
                candidates=candidate_evidence,
            )
            adjudication_records.append(report.model_dump(mode="json"))
            if report.classifications and not any(
                item.relation.value in {"ambiguous", "unclassified"} and item.material
                for item in report.classifications
            ):
                self._resolved_requirement_ids.add(requirement.artifact_id)
            classifications.extend(
                InstalledCandidateClassification(
                    artifact_id=item.artifact_id,
                    requirement_artifact_id=item.requirement_artifact_id,
                    claim_artifact_id=item.claim_artifact_id,
                    evidence_artifact_id=item.evidence_artifact_id,
                    relation=item.relation.value,
                    rationale=item.rationale,
                    method=item.method.value,
                    confidence=item.confidence,
                    material=item.material,
                    record=item.model_dump(mode="json"),
                )
                for item in report.classifications
            )
        search = InstalledResearchSearch(
            artifact_id=counter_run.artifact_id,
            document_artifact_ids=tuple(
                dict.fromkeys(item.document_id for item in candidate_evidence)
            ),
            records=tuple(
                InstalledResearchSearchRecord(
                    claim_artifact_id=record.claim_artifact_id,
                    outcome=record.outcome.value,
                    candidate_evidence_artifact_ids=(
                        record.candidate_evidence_artifact_ids
                    ),
                    negative_search_statement=record.negative_search_statement,
                    record=record.model_dump(mode="json"),
                    requirement_artifact_id=attempt.requirement_artifact_id,
                    target_claim_artifact_ids=attempt.target_claim_artifact_ids,
                    attempt_artifact_id=attempt.artifact_id,
                    classifications=tuple(
                        item
                        for item in classifications
                        if item.evidence_artifact_id
                        in record.candidate_evidence_artifact_ids
                    ),
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
            adjudication_records=tuple(adjudication_records),
        )
        self._search_history.append(search)
        return search

    def evaluate(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
        search: InstalledResearchSearch | None,
    ) -> InstalledResearchConvergence:
        del plan, search
        material_requirements = tuple(
            item for item in request.requirements if item.material
        )
        satisfied_requirements = tuple(
            item
            for item in material_requirements
            if item.satisfied or item.artifact_id in self._resolved_requirement_ids
        )
        remaining_requirements = tuple(
            item for item in material_requirements if item not in satisfied_requirements
        )
        satisfied_ids = tuple(
            self._requirement_reference(item) for item in satisfied_requirements
        )
        remaining_ids = tuple(
            self._requirement_reference(item) for item in remaining_requirements
        )
        candidate_ids = tuple(
            dict.fromkeys(
                artifact_id
                for completed_search in self._search_history
                for record in completed_search.records
                for artifact_id in record.candidate_evidence_artifact_ids
            )
        )
        classifications = tuple(
            classification
            for completed_search in self._search_history
            for record in completed_search.records
            for classification in record.classifications
        )
        classified_candidate_ids = {
            item.evidence_artifact_id for item in classifications
        }
        unresolved_classification_ids = tuple(
            dict.fromkeys(
                tuple(
                    item.artifact_id
                    for item in classifications
                    if item.material and item.relation in {"ambiguous", "unclassified"}
                )
                + tuple(
                    artifact_id
                    for artifact_id in candidate_ids
                    if artifact_id not in classified_candidate_ids
                )
            )
        )
        unsearched = tuple(
            dict.fromkeys(
                artifact_id
                for completed_search in self._search_history
                for artifact_id in (
                    completed_search.unsearched_important_claim_artifact_ids
                )
            )
        )
        blocking_ids = tuple(
            dict.fromkeys(remaining_ids + unresolved_classification_ids + unsearched)
        )
        marginal_values, latest_new_evidence_count = self._marginal_evidence_values()
        revision = self._revision
        current_graph_id = (
            self._claim_graph_artifact_id
            if revision is None
            else revision.revised_answer.artifact_id
        )
        answer_status = AnswerVerificationStatus(
            request.grounding_admission_outcome
            if revision is None
            else revision.revised_answer.outcome.value
        )
        contextualized = self._claim_graph.get("contextualized")
        initial_conflicts = (
            contextualized.get("conflicts")
            if isinstance(contextualized, dict)
            else None
        )
        evidence = create_research_convergence_evidence(
            current_graph_artifact_id=current_graph_id,
            material_requirement_count=len(material_requirements),
            satisfied_requirement_artifact_ids=satisfied_ids,
            remaining_requirement_artifact_ids=remaining_ids,
            material_candidate_count=len(candidate_ids),
            classified_candidate_count=len(
                set(candidate_ids) & classified_candidate_ids
            ),
            unresolved_classification_artifact_ids=(unresolved_classification_ids),
            blocking_gap_artifact_ids=blocking_ids,
            unsearched_important_claim_artifact_ids=unsearched,
            answer_verification_status=answer_status,
            answer_revision_artifact_id=(
                None if revision is None else revision.artifact_id
            ),
            material_conflict_count=(
                len(initial_conflicts) if isinstance(initial_conflicts, list) else 0
            )
            if revision is None
            else len(revision.revised_answer.contextualized.conflicts),
            marginal_evidence_values=marginal_values,
        )
        at_hard_limit = (
            self._search_count >= self._convergence.policy.max_tool_calls
            or 1 >= self._convergence.policy.max_elapsed_ms
        )
        observation = create_convergence_observation(
            iteration=1,
            graph_artifact_id=current_graph_id,
            coverage=evidence.requirement_coverage,
            verified_answerable_claims=len(satisfied_ids),
            required_claims=len(material_requirements),
            blocking_gap_count=len(blocking_ids),
            new_evidence_count=latest_new_evidence_count,
            marginal_evidence_value=(
                0.0 if not marginal_values else marginal_values[-1]
            ),
            cumulative_tool_calls=self._search_count,
            cumulative_tokens=0,
            cumulative_elapsed_ms=1,
            explicit_insufficiency=(
                not material_requirements
                or (
                    not at_hard_limit
                    and (
                        bool(blocking_ids)
                        or answer_status is AnswerVerificationStatus.abstained
                    )
                )
            ),
        )
        decision = self._convergence.evaluate((observation,), evidence=evidence)
        return InstalledResearchConvergence(
            artifact_id=decision.artifact_id,
            outcome=decision.outcome.value,
            stop=decision.stop,
            record=decision.model_dump(mode="json"),
        )

    @staticmethod
    def _requirement_reference(requirement: InstalledResearchRequirement) -> str:
        return requirement.source_requirement_artifact_id or requirement.artifact_id

    def _marginal_evidence_values(self) -> tuple[tuple[float, ...], int]:
        seen: set[str] = set()
        values: list[float] = []
        latest_new_count = 0
        for search in self._search_history:
            candidate_ids = tuple(
                dict.fromkeys(
                    artifact_id
                    for record in search.records
                    for artifact_id in record.candidate_evidence_artifact_ids
                )
            )
            new_ids = tuple(item for item in candidate_ids if item not in seen)
            latest_new_count = len(new_ids)
            values.append(
                0.0 if not candidate_ids else len(new_ids) / len(candidate_ids)
            )
            seen.update(candidate_ids)
        return tuple(values), latest_new_count


def _research_request(
    claim_graph: dict[str, object],
    *,
    graph_artifact_id: str,
    counterevidence_policy_artifact_id: str,
    convergence_policy_artifact_id: str,
    max_searches: int,
    maximum_search_candidates: int,
    budget_limits: BudgetDimensions,
) -> InstalledResearchRequest:
    raw_claim_set = claim_graph.get("claims")
    raw_packet = claim_graph.get("evidence_packet")
    raw_verification = claim_graph.get("citation_verification")
    raw_synthesis = claim_graph.get("synthesis")
    raw_admission = claim_graph.get("grounding_admission")
    if (
        not isinstance(raw_claim_set, dict)
        or not isinstance(raw_packet, dict)
        or not isinstance(raw_verification, dict)
        or not isinstance(raw_synthesis, dict)
        or not isinstance(raw_admission, dict)
    ):
        raise StepDispatchError("claim graph reasoning records are invalid")
    raw_claims = raw_claim_set.get("claims")
    raw_verified = raw_verification.get("claims")
    if not isinstance(raw_claims, list) or not isinstance(raw_verified, list):
        raise StepDispatchError("claim graph claims or verification are invalid")
    try:
        requirement_plan = AnswerRequirementPlanningService().plan(
            question=_required_string(claim_graph.get("query"), "research question"),
            graph_artifact_id=graph_artifact_id,
            scope_artifact_id=_required_string(
                raw_packet.get("scope_artifact_id"),
                "scope_artifact_id",
            ),
            claims=NormalizedClaimSet.model_validate(raw_claim_set),
            verification=CitationVerificationReport.model_validate(raw_verification),
            admission=GroundingAdmissionDecision.model_validate(raw_admission),
            synthesis=CredentialFreeSynthesis.model_validate(raw_synthesis),
        )
    except (ValidationError, ValueError) as error:
        raise StepDispatchError(
            "claim graph cannot produce a valid answer requirement plan"
        ) from error
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
            item.status is AnswerRequirementStatus.SATISFIED
            for item in requirement_plan.requirements
            if item.kind is AnswerRequirementKind.FINDING
        ),
        counterevidence_policy_artifact_id=counterevidence_policy_artifact_id,
        convergence_policy_artifact_id=convergence_policy_artifact_id,
        question=_required_string(claim_graph.get("query"), "research question"),
        requirements=tuple(
            InstalledResearchRequirement.create(
                description=item.description,
                claim_artifact_id=(
                    item.target_claim_artifact_ids[0]
                    if len(item.target_claim_artifact_ids) == 1
                    else None
                ),
                satisfied=item.status is AnswerRequirementStatus.SATISFIED,
                kind=item.kind.value,
                status=item.status.value,
                priority=item.priority,
                material=item.material,
                target_claim_artifact_ids=item.target_claim_artifact_ids,
                dependency_requirement_artifact_ids=(
                    item.dependency_requirement_artifact_ids
                ),
                satisfaction_criteria=item.satisfaction_criteria,
                query_text=item.query_text,
                evidence_artifact_ids=item.evidence_artifact_ids,
                source_gap_artifact_ids=item.source_gap_artifact_ids,
                source_requirement_artifact_id=item.artifact_id,
            )
            for item in requirement_plan.requirements
        ),
        evidence_relations=tuple(relations),
        max_searches=max_searches,
        requirement_plan_artifact_id=requirement_plan.artifact_id,
        requirement_plan_record=requirement_plan.model_dump(mode="json"),
        requirement_plan_outcome=requirement_plan.outcome.value,
        budget_limits=budget_limits,
        maximum_search_candidates=maximum_search_candidates,
        grounding_admission_outcome=_required_string(
            raw_admission.get("outcome"),
            "grounding admission outcome",
        ),
    )


class CanonicalAgentOperationAdapter:
    """Run one skeptical, budget-terminated research critique cycle."""

    adapter_id = "bijux-canon-agent:bounded-research-critique:v1"
    adapter_version = "1.0"
    operation = DagOperation.AGENT

    @staticmethod
    def accepts_cooperative_cancellation(
        artifacts: tuple[StepOutputArtifact, ...],
    ) -> bool:
        """Accept only an exact Agent cancellation terminal as partial success."""
        if len(artifacts) != 1 or artifacts[0].contract_id != "agent.research-trace.v1":
            return False
        try:
            payload = _json_object(artifacts[0].artifact, "agent.research-trace.v1")
        except StepDispatchError:
            return False
        outcome = payload.get("research_outcome")
        signal = payload.get("cancellation_signal")
        return (
            payload.get("status") == "cancelled"
            and isinstance(outcome, dict)
            and outcome.get("kind") == "cancelled"
            and isinstance(signal, dict)
            and outcome.get("cancellation_artifact_id") == signal.get("artifact_id")
        )

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
            raw_claim_set.get("claims") if isinstance(raw_claim_set, dict) else None
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
            max_tool_calls=2,
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
            maximum_search_candidates=counter_policy.top_k,
            budget_limits=BudgetDimensions(
                iterations=convergence_policy.max_tool_calls * 2 + 2,
                retrievals=convergence_policy.max_tool_calls,
                documents=(
                    convergence_policy.max_tool_calls * counter_policy.top_k
                ),
                candidates=(
                    convergence_policy.max_tool_calls * counter_policy.top_k
                ),
                evidence_items=(
                    convergence_policy.max_tool_calls * counter_policy.top_k
                ),
                tool_calls=convergence_policy.max_tool_calls,
                tokens=step.inputs.budget.max_provider_tokens or 0,
                elapsed_ms=max(
                    1,
                    int(step.inputs.budget.timeout_seconds * 1000),
                ),
                memory_bytes=step.inputs.budget.max_artifact_bytes,
                artifact_bytes=step.inputs.budget.max_artifact_bytes,
            ),
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
                claim_graph=claim_graph,
                claim_graph_artifact_id=graph_id,
            ),
            _RuntimeCancellationPort(
                context,
                content_artifact_id(
                    {
                        "request_id": str(step.inputs.request_id),
                        "step_id": step.step_id,
                    }
                ),
            ),
        )
        payload = canonical_json_bytes(
            {
                "answer": (
                    claim_graph.get("answer")
                    if research.revision is None
                    else research.revision.after_answer
                ),
                "answer_revision": (
                    None
                    if research.revision is None
                    else dict(research.revision.record)
                ),
                "answer_revision_artifact_id": (
                    None
                    if research.revision is None
                    else research.revision.artifact_id
                ),
                "answer_requirement_plan": dict(request.requirement_plan_record),
                "budget_decisions": [
                    _json_value(asdict(item)) for item in research.budget_decisions
                ],
                "budget_policy": {
                    "artifact_id": research.budget_policy.artifact_id,
                    "global_limits": research.budget_policy.global_limits.payload(),
                    "plan_sha256": research.budget_policy.plan_sha256,
                    "role_limits": {
                        role: limits.payload()
                        for role, limits in research.budget_policy.role_limits.items()
                    },
                },
                "budget_policy_artifact_id": research.budget_policy_artifact_id,
                "budget_usage": research.budget_usage.payload(),
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
                "counterevidence_plans": [
                    dict(item.record) for item in research.plan_history
                ],
                "targeted_search_plan": (
                    None
                    if research.plan.targeted_search_plan is None
                    else _json_value(asdict(research.plan.targeted_search_plan))
                ),
                "targeted_search_plans": [
                    (
                        None
                        if item.targeted_search_plan is None
                        else _json_value(asdict(item.targeted_search_plan))
                    )
                    for item in research.plan_history
                ],
                "targeted_search_observations": [
                    _json_value(asdict(item))
                    for item in research.targeted_search_observations
                ],
                "counterevidence_retrieval_artifact_ids": (
                    []
                    if research.search is None
                    else list(research.search.retrieval_artifact_ids)
                ),
                "counterevidence_document_artifact_ids": list(
                    document_id
                    for item in research.search_history
                    for document_id in item.document_artifact_ids
                ),
                "counterevidence_retrievals": (
                    []
                    if research.search is None
                    else [dict(item) for item in research.search.retrieval_records]
                ),
                "counterevidence_run": (
                    None if research.search is None else dict(research.search.record)
                ),
                "counterevidence_runs": [
                    dict(item.record) for item in research.search_history
                ],
                "candidate_adjudications": [
                    dict(record)
                    for item in research.search_history
                    for record in item.adjudication_records
                ],
                "candidate_classifications": [
                    dict(classification.record)
                    for item in research.search_history
                    for record in item.records
                    for classification in record.classifications
                ],
                "cancellation_signal": (
                    None
                    if research.cancellation_signal is None
                    else _json_value(asdict(research.cancellation_signal))
                ),
                "generation_id": generation_id,
                "grounding_admission_outcome": request.grounding_admission_outcome,
                "insufficiencies": list(research.insufficiencies),
                "opposition_candidates": list(research.opposition_candidate_ids),
                "research_candidates": list(research.opposition_candidate_ids),
                "relation_status": research.relation_status,
                "research_state": research.final_state.to_record(),
                "research_state_history": [
                    state.to_record() for state in research.state_history
                ],
                "research_outcome": research.terminal_outcome.to_record(),
                "schema_version": "bijux.canon.agent.research_trace.v1",
                "status": research.terminal_outcome.kind.value,
                "convergence_status": research.convergence.outcome,
                "termination": dict(research.convergence.record),
                "tool_failure_artifact_ids": list(research.tool_failure_artifact_ids),
            }
        )
        if research.terminal_outcome.kind.value != "cancelled":
            context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="agent.research-trace.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


__all__ = ["CanonicalAgentOperationAdapter"]
