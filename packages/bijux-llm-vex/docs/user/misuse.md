# bijux-vex misuse patterns (real-world)

This page lists ways people are likely to misuse bijux-vex and the exact failure surfaces they will hit.

- Treating bijux-vex as a “vector database”: requests that expect CRUD or implicit persistence will fail with `InvariantError` or `BackendCapabilityError`; refer to `docs/user/not_a_vdb.md`.
- Requesting non-deterministic execution without ANN support: fails with `NDExecutionUnavailableError` (HTTP 503 / CLI non-zero) and an audit entry explaining missing `supports_ann`.
- Supplying string intents or modes: boundary coercion now rejects unknown values with `InvariantError`.
- Mixing deterministic replay with ND artifacts: replay refuses with `ReplayNotSupportedError` and provenance notes the contract mismatch.
- Ignoring budgets: deterministic runs reject pre-execution if budgets are impossible; ND runs emit `BudgetExceededError` with provenance.

Always consult the contract docs before extending usage beyond the supported execution model.
