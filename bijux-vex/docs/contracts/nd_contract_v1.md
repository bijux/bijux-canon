# ND Contract v1 (Non-Deterministic Execution)

**Status:** Experimental behavior, stable contract surface.  
**Applies to:** `ExecutionContract.NON_DETERMINISTIC` (see maturity model in `ExecutionContract.support_level`).

This contract formalizes what ND execution is allowed to do, what it must report, and how refusal is represented. ND is **not** a mode; it is a contract with explicit obligations.

## 1) What ND Is Allowed To Do

ND execution **may**:

- Use approximate or heuristic algorithms (ANN, sampling, pruning).
- Return results that differ in rank order or score from exact execution.
- Emit bounded divergence instead of bit-identical replay.
- Refuse execution when declared requirements cannot be met.

ND execution **may not**:

- Proceed without a declared randomness profile and budget.
- Hide randomness sources or approximation parameters.
- Silently fall back to exact unless explicitly documented and reported.

## 2) What ND Must Report

Every ND result **must** include:

- **Approximation report** (`ApproximationReport`)
  - `algorithm`, `algorithm_version`, `backend`
  - `randomness_sources`
  - `index_parameters` and `query_parameters`
  - `allowed_rank_jitter`, `allowed_recall_drop`
  - Any fallback flags (e.g., `deterministic_fallback_used`)
- **Determinism report** (`DeterminismReport`)
  - `randomness_sources`
  - `reproducibility_bounds`
- **Randomness profile** (seed and/or declared sources, bounded flag)
- **Budget envelope** (latency/memory/error limits, as applicable)

These reports are part of the ND audit trail and **must** be persisted in execution artifacts/provenance.

## 3) Refusal Shape (ND)

If ND execution is rejected, the refusal payload **must** be machine-readable and include:

- `reason`
- `message`
- `remediation`

Examples of ND refusals:

- `reason: determinism_violation` → missing randomness profile or bounds
- `reason: backend_capability_missing` → backend cannot honor ND/ANN
- `reason: budget_exceeded` → ND budget cannot be satisfied

ND refusals are not silent fallbacks. The caller must decide whether to adjust parameters or switch contracts.

## 4) Maturity Model Tie-In

The contract surface is stable and enforced:

- `ExecutionContract.NON_DETERMINISTIC.support_level` = `STABLE_BOUNDED`
- `ExecutionContract.NON_DETERMINISTIC.maturity` = `EXPERIMENTAL`

This means the **contract is fixed**, but the behavior may evolve under explicit, audited changes.

## 5) Enforcement Summary

ND execution is valid **only if** all conditions hold:

- Explicit contract is `NON_DETERMINISTIC`.
- Randomness profile is present (seed and/or sources).
- Execution budget is present.
- Approximation + determinism reports are emitted and persisted.
- Refusals are explicit and structured (no silent fallback).
