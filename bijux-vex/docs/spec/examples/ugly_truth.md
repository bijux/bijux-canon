# Limitations and failure modes (descriptive)

Scenario: ND ANN execution with budget exhaustion, approximation, provenance, and replay mismatch.

Steps (CLI narrative):

1. `bijux vex materialize --execution-contract non_deterministic`
2. `bijux vex execute --artifact-id art-1 --vector "[...]" --top-k 1 --execution-contract non_deterministic --execution-intent exploratory_search --execution-mode bounded --randomness-seed 1 --randomness-sources reference_ann_hnsw --randomness-bounded --max-latency-ms 1 --max-memory-mb 1 --max-error 0.2`
3. Execution returns PARTIAL with `BudgetExceededError` provenance and `DeterminismReport`.
4. Ledger stores `ExecutionResult` + artifact signature.
5. `bijux vex replay --request-text "..."` → mismatch allowed but recorded; `ReplayOutcome.details` carries divergence and randomness sources.
6. `bijux vex compare --vector "[...]" --execution-intent exact_validation` → overlap/recall deltas highlight approximation loss.

What it proves:

- Budgets abort mid-plan, not post-hoc.
- ND replay is legal but must declare divergence.
- Provenance is required; replay without ledger state fails fast.
- Approximation is auditable, not silent.
