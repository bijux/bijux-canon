# Failure semantics (spec)

This document explains how failures propagate through the pipeline and into artifacts.

## Where failures appear

Failures can surface in:

- the pipeline result (`final_status`)
- trace entries (`failure_artifact`)
- API responses (`error` object)

The representation is intentionally redundant: the *verdict summary* is for humans,
the *trace* is for auditing and tooling.

## Recoverable vs non-recoverable

A failure artifact includes `recoverable`:

- `recoverable: true` means the orchestrator MAY attempt a recovery strategy (e.g. retry)
- `recoverable: false` means the run MUST terminate (or move to a non-retry fallback path)

Recoverability is constrained by the failure class profile; see `docs/spec/failure_model.md`.

## Operational vs epistemic failures

- **Operational failures**: timeouts, resource exhaustion, validation errors, etc.
- **Epistemic failures**: the system cannot justify a confident decision (e.g. insufficient evidence)

Epistemic failures are not “bugs”; they are explicit outcomes that preserve honesty.

## Trace replayability interaction

Some failures are replayable (safe to validate deterministically), others are not.
If a failure is non-replayable, replay tooling MUST not claim deterministic reproducibility.

## Contractual rule

If a failure artifact violates taxonomy or profiles, the system MUST fail fast rather than emit an invalid trace.
