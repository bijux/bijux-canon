"""Terminal honesty contracts for installed research."""

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_agent.application import (
    InstalledResearchTerminalKind,
    InstalledResearchTerminalOutcome,
    RemainingResearchWork,
)

_CONVERGENCE = "sha256:" + "1" * 64
_REQUIREMENT = "sha256:" + "2" * 64
_EVIDENCE = "sha256:" + "3" * 64
_GAP = "sha256:" + "4" * 64
_CLAIM = "sha256:" + "5" * 64
_CANCELLATION = "sha256:" + "6" * 64
_FAILURE = "sha256:" + "7" * 64


def _remaining() -> RemainingResearchWork:
    return RemainingResearchWork.create(
        unsatisfied_requirement_artifact_ids=(_REQUIREMENT,),
        unresolved_evidence_artifact_ids=(_EVIDENCE,),
        unresolved_gap_artifact_ids=(_GAP,),
        unsearched_important_claim_artifact_ids=(_CLAIM,),
        descriptions=("One important claim remains unsearched.",),
    )


def test_terminal_outcomes_are_disjoint_and_content_addressed() -> None:
    empty = RemainingResearchWork.create()
    converged = InstalledResearchTerminalOutcome.create(
        kind=InstalledResearchTerminalKind.CONVERGED,
        convergence_artifact_id=_CONVERGENCE,
        convergence_outcome="converged",
        remaining_work=empty,
    )
    budget = InstalledResearchTerminalOutcome.create(
        kind=InstalledResearchTerminalKind.INCOMPLETE_BUDGET,
        convergence_artifact_id=_CONVERGENCE,
        convergence_outcome="budget_exhausted",
        remaining_work=_remaining(),
        exhausted_budget_dimensions=("retrievals",),
    )
    cancelled = InstalledResearchTerminalOutcome.create(
        kind=InstalledResearchTerminalKind.CANCELLED,
        convergence_artifact_id=_CONVERGENCE,
        convergence_outcome="cancelled",
        remaining_work=_remaining(),
        cancellation_artifact_id=_CANCELLATION,
    )
    failed = InstalledResearchTerminalOutcome.create(
        kind=InstalledResearchTerminalKind.FAILED,
        convergence_artifact_id=_CONVERGENCE,
        convergence_outcome="failed",
        remaining_work=_remaining(),
        failure_artifact_ids=(_FAILURE,),
    )

    assert (
        len(
            {
                converged.artifact_id,
                budget.artifact_id,
                cancelled.artifact_id,
                failed.artifact_id,
            }
        )
        == 4
    )
    assert budget.to_record()["remaining_work"] == _remaining().to_record()


def test_false_completion_and_unnamed_budget_work_are_rejected() -> None:
    converged = InstalledResearchTerminalOutcome.create(
        kind=InstalledResearchTerminalKind.CONVERGED,
        convergence_artifact_id=_CONVERGENCE,
        convergence_outcome="converged",
        remaining_work=RemainingResearchWork.create(),
    )

    with pytest.raises(ValueError, match="cannot retain incomplete"):
        replace(converged, remaining_work=_remaining())
    with pytest.raises(ValueError, match="must name budget and work"):
        InstalledResearchTerminalOutcome.create(
            kind=InstalledResearchTerminalKind.INCOMPLETE_BUDGET,
            convergence_artifact_id=_CONVERGENCE,
            convergence_outcome="budget_exhausted",
            remaining_work=_remaining(),
        )
    with pytest.raises(ValueError, match="cancellation identity"):
        InstalledResearchTerminalOutcome.create(
            kind=InstalledResearchTerminalKind.CANCELLED,
            convergence_artifact_id=_CONVERGENCE,
            convergence_outcome="cancelled",
            remaining_work=_remaining(),
        )
