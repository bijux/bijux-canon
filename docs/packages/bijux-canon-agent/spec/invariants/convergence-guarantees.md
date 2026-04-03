# Convergence guarantees (spec)

Convergence is a mechanism for stopping iterative refinement when decisions become stable.

## What the system guarantees

- The pipeline MAY iterate multiple times.
- The final status MUST record:
  - whether the run converged,
  - the number of iterations executed,
  - a convergence reason (when relevant).

## What the system does not guarantee

- Convergence does not imply correctness.
- Convergence thresholds are configuration-dependent and may change between versions.

## Practical guidance

- Prefer convergence strategies that are explainable from artifacts (verdict stability, mixed stability).
- Avoid “hidden” convergence logic that cannot be justified from recorded scores/verdicts.
