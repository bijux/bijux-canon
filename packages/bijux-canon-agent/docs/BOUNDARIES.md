# BOUNDARIES

`bijux-canon-agent` owns agent orchestration, trace-backed execution, and final-result assembly.

It does own:
- reusable agent lifecycle and pipeline coordination
- package CLI and HTTP boundaries
- trace and replay-facing agent artifacts

It does not own:
- canonical runtime persistence or replay governance from `bijux-canon-runtime`
- retrieval/index execution internals from `bijux-canon-ingest` and `bijux-canon-index`
- reasoning policy engines from `bijux-canon-reason`

When a concern is package-specific orchestration, it belongs here. When it is cross-package runtime authority or domain-specific execution logic, it belongs elsewhere.
