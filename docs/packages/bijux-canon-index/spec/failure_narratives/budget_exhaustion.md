# Failure narrative: budget exhaustion

- **Invariant**: INV-021 (budget exhaustion must be explicit and halt progress).
- **Trigger**: ExecutionBudget limit (vectors/latency/probes) exceeded mid-plan.
- **Response**:
  - Status becomes PARTIAL.
  - BudgetExceededError (value) recorded with dimension.
  - Replay still allowed; divergence expected for ND.
- **Evidence**:
  - ExecutionResult.status == PARTIAL
  - Failure reason includes `budget_exhausted_<dimension>`
  - Scenario: docs/spec/examples/forcing_case.md; tests/scenarios/test_forcing_case.py
