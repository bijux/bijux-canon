# External misuse to avoid

- Treating bijux-vex as a vector DB: there is no CRUD, indexing API, or serving tier; executions are contract-bound.
- Expecting ANN replay: ND executions provide approximation envelopes and audit but do not promise ANN result equality.
- Assuming implicit defaults: intents, contracts, and modes are mandatory; unknown strings are rejected.
- Using ND without budgets: bounded/exploratory modes require explicit budgets and randomness profiles.

Use bijux-vex when you need audited execution comparisons, not managed vector storage.
