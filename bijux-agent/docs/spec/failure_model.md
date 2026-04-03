# Failure model (spec)

Failures are represented as immutable `FailureArtifact` objects.

## `FailureArtifact` fields

A failure artifact MUST include:

- `failure_class` — machine-actionable classification
- `category` — `operational_failure` or `epistemic_failure`
- `phase` — canonical phase where the failure occurred
- `recoverable` — whether the runner may attempt recovery
- `mode` and `message` — how the failure was detected and what happened

## Failure classes and profiles

Each `FailureClass` has a profile defining retryability, replayability, and category.
The profile is the source of truth for how the runner and tooling may react.

| FailureClass | Category | Retryable | Replayable |
| --- | --- | --- | --- |
| `validation_error` | operational | No | Yes |
| `execution_error` | operational | Yes | No |
| `resource_exhaustion` | operational | Yes | No |
| `fatal_failure` | operational | No | No |
| `user_interruption` | operational | No | Yes |
| `budget_exceeded` | operational | No | Yes |
| `max_iterations` | operational | No | Yes |
| `verification_veto` | operational | No | Yes |
| `epistemic_uncertainty` | epistemic | No | Yes |

## Invariants

- Every `FailureClass` MUST have a profile.
- A failure artifact’s `category` MUST match the profile’s category.
- If `recoverable` is true, the profile MUST mark the class retryable.

(Implementation reference: `src/bijux_agent/pipeline/results/failure.py`.)
