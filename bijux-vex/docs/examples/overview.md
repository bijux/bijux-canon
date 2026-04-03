# Examples overview

Use these scenarios to learn the system quickly. Follow them in order.

1) **Exact execution**: `spec/examples/exact_execution.md`

   - Run a deterministic query, inspect replayable artifacts.
2) **ANN execution (experimental)**: `spec/examples/ann_execution.md`

   - Run a non-deterministic query with an ANN runner, see approximation reports.
3) **Deterministic replay**: `spec/examples/deterministic_replay.md`

   - Prove deterministic outputs match across runs.
4) **ND execution with audit**: `spec/examples/nd_execution_with_audit.md`

   - Inspect randomness, approximation metadata, and replay envelopes.
5) **Forcing case**: `spec/examples/forcing_case.md`

   - Combined budget exhaustion + fallback + divergence audit.
6) **Limitations and failure modes**: `spec/examples/ugly_truth.md`

   - Understand how and why executions can fail.
7) **Contract violation**: `examples/contract_violation.md`

   - Intentional misuse: ND requested without ANN support returns `NDExecutionUnavailableError`.

Tips:

- Cross-check each example with the API schema (`api/v1/schema.yaml`) if using HTTP.
- Keep the non-goals in mind: this is not a vector DB or RAG system.
