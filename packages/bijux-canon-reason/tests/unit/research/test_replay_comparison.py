# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Immutable research reasoning replay and comparison tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    ResearchAttemptComparison,
    ResearchChangeAction,
    ResearchChangeAuthority,
    ResearchGraphEventKind,
    ResearchGraphSurface,
    ResearchReasoningAttempt,
    ResearchReasoningReplayService,
    ResearchReplayError,
    ResearchReplayErrorCode,
    ReplayedResearchAttempt,
    create_research_graph_event,
    create_research_reasoning_attempt,
)


def _id(value: str) -> str:
    return content_artifact_id({"test": value})


def _events(specifications):
    events = []
    for sequence, (kind, target, authority) in enumerate(specifications, start=1):
        previous = events[-1].artifact_id if events else None
        events.append(
            create_research_graph_event(
                sequence=sequence,
                previous_event_artifact_id=previous,
                kind=kind,
                target_artifact_id=target,
                authority=authority,
                authority_provenance_artifact_id=_id(
                    "deterministic-policy"
                    if authority is ResearchChangeAuthority.deterministic
                    else "provider-provenance"
                ),
            )
        )
    return tuple(events)


def _attempt_chain():
    claim_1, claim_2 = _id("claim-1"), _id("claim-2")
    evidence_1, evidence_2 = _id("evidence-1"), _id("evidence-2")
    decision_1, decision_2 = _id("decision-1"), _id("decision-2")
    root = create_research_reasoning_attempt(
        research_input_artifact_ids=(_id("question"), _id("packet-1")),
        events=_events(
            (
                (
                    ResearchGraphEventKind.claim_admitted,
                    claim_1,
                    ResearchChangeAuthority.provider_mediated,
                ),
                (
                    ResearchGraphEventKind.evidence_admitted,
                    evidence_1,
                    ResearchChangeAuthority.deterministic,
                ),
                (
                    ResearchGraphEventKind.decision_recorded,
                    decision_1,
                    ResearchChangeAuthority.deterministic,
                ),
            )
        ),
    )
    root_state = ResearchReasoningReplayService().replay_chain((root,))[0]
    child = create_research_reasoning_attempt(
        research_input_artifact_ids=(_id("question"), _id("packet-2")),
        parent_attempt_artifact_id=root.artifact_id,
        base_state_artifact_id=root_state.state_artifact_id,
        events=_events(
            (
                (
                    ResearchGraphEventKind.claim_retracted,
                    claim_1,
                    ResearchChangeAuthority.deterministic,
                ),
                (
                    ResearchGraphEventKind.claim_admitted,
                    claim_2,
                    ResearchChangeAuthority.provider_mediated,
                ),
                (
                    ResearchGraphEventKind.evidence_retracted,
                    evidence_1,
                    ResearchChangeAuthority.deterministic,
                ),
                (
                    ResearchGraphEventKind.evidence_admitted,
                    evidence_2,
                    ResearchChangeAuthority.deterministic,
                ),
                (
                    ResearchGraphEventKind.decision_superseded,
                    decision_1,
                    ResearchChangeAuthority.deterministic,
                ),
                (
                    ResearchGraphEventKind.decision_recorded,
                    decision_2,
                    ResearchChangeAuthority.deterministic,
                ),
            )
        ),
    )
    return root, child


def test_replays_immutable_attempts_and_attributes_every_graph_change() -> None:
    root, child = _attempt_chain()
    service = ResearchReasoningReplayService()

    replayed = service.replay_chain((root, child))
    comparison = service.compare(
        baseline=replayed[0], current=replayed[1], current_attempt=child
    )
    restarted_replays = tuple(
        ReplayedResearchAttempt.model_validate_json(item.model_dump_json())
        for item in replayed
    )
    restarted_comparison = ResearchAttemptComparison.model_validate_json(
        comparison.model_dump_json()
    )

    assert restarted_replays == replayed
    assert restarted_comparison == comparison
    assert len(comparison.added_claim_artifact_ids) == 1
    assert len(comparison.removed_claim_artifact_ids) == 1
    assert len(comparison.added_evidence_artifact_ids) == 1
    assert len(comparison.removed_evidence_artifact_ids) == 1
    assert len(comparison.added_decision_artifact_ids) == 1
    assert len(comparison.removed_decision_artifact_ids) == 1
    assert len(comparison.attributions) == 6
    assert {item.authority for item in comparison.attributions} == {
        ResearchChangeAuthority.deterministic,
        ResearchChangeAuthority.provider_mediated,
    }
    provider_change = next(
        item
        for item in comparison.attributions
        if item.authority is ResearchChangeAuthority.provider_mediated
    )
    assert provider_change.surface is ResearchGraphSurface.claim
    assert provider_change.action is ResearchChangeAction.added
    assert comparison.added_input_artifact_ids
    assert comparison.removed_input_artifact_ids
    assert not comparison.identical_graph_state


def test_empty_delta_replays_to_identical_graph_state() -> None:
    root, _ = _attempt_chain()
    service = ResearchReasoningReplayService()
    root_state = service.replay_chain((root,))[0]
    child = create_research_reasoning_attempt(
        research_input_artifact_ids=root.research_input_artifact_ids,
        parent_attempt_artifact_id=root.artifact_id,
        base_state_artifact_id=root_state.state_artifact_id,
        events=(),
    )
    replayed = service.replay_chain((root, child))
    comparison = service.compare(
        baseline=replayed[0], current=replayed[1], current_attempt=child
    )

    assert comparison.identical_graph_state
    assert not comparison.attributions
    assert replayed[0].state_artifact_id == replayed[1].state_artifact_id


def test_replay_rejects_empty_history_and_invalid_transition() -> None:
    service = ResearchReasoningReplayService()
    with pytest.raises(ResearchReplayError) as empty:
        service.replay_chain(())
    assert empty.value.code is ResearchReplayErrorCode.empty_attempt_chain

    attempt = create_research_reasoning_attempt(
        research_input_artifact_ids=(_id("question"),),
        events=_events(
            (
                (
                    ResearchGraphEventKind.claim_retracted,
                    _id("absent-claim"),
                    ResearchChangeAuthority.deterministic,
                ),
            )
        ),
    )
    with pytest.raises(ResearchReplayError) as transition:
        service.replay_chain((attempt,))
    assert transition.value.code is ResearchReplayErrorCode.invalid_transition


def test_replay_rejects_event_sequence_and_hash_chain_breaks() -> None:
    root, _ = _attempt_chain()
    service = ResearchReasoningReplayService()
    first = root.events[0]
    wrong_sequence = create_research_graph_event(
        sequence=2,
        previous_event_artifact_id=None,
        kind=first.kind,
        target_artifact_id=first.target_artifact_id,
        authority=first.authority,
        authority_provenance_artifact_id=first.provider_provenance_artifact_id
        or _id("x"),
    )
    broken_sequence = root.model_copy(
        update={"events": (wrong_sequence,) + root.events[1:]}
    )
    with pytest.raises(ResearchReplayError) as sequence:
        service.replay_chain((broken_sequence,))
    assert sequence.value.code is ResearchReplayErrorCode.event_sequence_mismatch

    second = root.events[1]
    wrong_chain = create_research_graph_event(
        sequence=2,
        previous_event_artifact_id=_id("wrong-previous"),
        kind=second.kind,
        target_artifact_id=second.target_artifact_id,
        authority=second.authority,
        authority_provenance_artifact_id=second.deterministic_policy_artifact_id
        or _id("x"),
    )
    broken_chain = root.model_copy(
        update={"events": (first, wrong_chain) + root.events[2:]}
    )
    with pytest.raises(ResearchReplayError) as chain:
        service.replay_chain((broken_chain,))
    assert chain.value.code is ResearchReplayErrorCode.event_chain_mismatch


def test_replay_rejects_authority_and_content_identity_tampering() -> None:
    root, _ = _attempt_chain()
    service = ResearchReasoningReplayService()
    first = root.events[0]
    no_provider = first.model_copy(update={"provider_provenance_artifact_id": None})
    broken_authority = root.model_copy(
        update={"events": (no_provider,) + root.events[1:]}
    )
    with pytest.raises(ResearchReplayError) as authority:
        service.replay_chain((broken_authority,))
    assert authority.value.code is (
        ResearchReplayErrorCode.authority_provenance_mismatch
    )

    changed_event = first.model_copy(
        update={"target_artifact_id": _id("changed-target")}
    )
    broken_event = root.model_copy(
        update={"events": (changed_event,) + root.events[1:]}
    )
    with pytest.raises(ResearchReplayError) as event_identity:
        service.replay_chain((broken_event,))
    assert event_identity.value.code is ResearchReplayErrorCode.event_identity_mismatch

    broken_attempt = root.model_copy(
        update={"research_input_artifact_ids": (_id("other"),)}
    )
    with pytest.raises(ResearchReplayError) as attempt_identity:
        service.replay_chain((broken_attempt,))
    assert attempt_identity.value.code is (
        ResearchReplayErrorCode.attempt_identity_mismatch
    )


def test_replay_rejects_parent_and_base_state_mismatch() -> None:
    root, child = _attempt_chain()
    service = ResearchReasoningReplayService()
    wrong_parent = create_research_reasoning_attempt(
        research_input_artifact_ids=child.research_input_artifact_ids,
        parent_attempt_artifact_id=_id("wrong-parent"),
        base_state_artifact_id=child.base_state_artifact_id,
        events=child.events,
    )
    with pytest.raises(ResearchReplayError) as parent:
        service.replay_chain((root, wrong_parent))
    assert parent.value.code is ResearchReplayErrorCode.parent_attempt_mismatch

    wrong_base = create_research_reasoning_attempt(
        research_input_artifact_ids=child.research_input_artifact_ids,
        parent_attempt_artifact_id=root.artifact_id,
        base_state_artifact_id=_id("wrong-base"),
        events=child.events,
    )
    with pytest.raises(ResearchReplayError) as base:
        service.replay_chain((root, wrong_base))
    assert base.value.code is ResearchReplayErrorCode.base_state_mismatch


def test_attempt_model_requires_matching_authority_and_parent_fields() -> None:
    event = create_research_graph_event(
        sequence=1,
        previous_event_artifact_id=None,
        kind=ResearchGraphEventKind.claim_admitted,
        target_artifact_id=_id("claim"),
        authority=ResearchChangeAuthority.provider_mediated,
        authority_provenance_artifact_id=_id("provider"),
    )
    payload = event.model_dump(mode="python")
    payload["deterministic_policy_artifact_id"] = _id("policy")
    with pytest.raises(ValidationError, match="matching provenance"):
        type(event).model_validate(payload)

    attempt_payload = {
        "schema_version": "bijux.canon.reason.research_reasoning_attempt.v1",
        "artifact_id": _id("attempt"),
        "research_input_artifact_ids": (_id("input"),),
        "parent_attempt_artifact_id": _id("parent"),
        "base_state_artifact_id": None,
        "events": (),
    }
    with pytest.raises(ValidationError, match="declared together"):
        ResearchReasoningAttempt.model_validate(attempt_payload)


def test_comparison_requires_directly_adjacent_attempts() -> None:
    root, child = _attempt_chain()
    service = ResearchReasoningReplayService()
    replayed = service.replay_chain((root, child))

    with pytest.raises(ResearchReplayError) as error:
        service.compare(baseline=replayed[1], current=replayed[0], current_attempt=root)
    assert error.value.code is ResearchReplayErrorCode.nonadjacent_comparison
