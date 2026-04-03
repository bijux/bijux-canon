# Architectural debt log

- **Layer gap**: Services vs orchestration remain split for public surface stability. Remove when CLI/tests can depend directly on `_orchestrator`.
- **Policy flattening**: Temporary removal of `core/policy`; revisit when compliance rules need isolation.
- **Error-as-value**: Only one path uses `ExecutionOutcome`; widen once callers migrate away from exceptions.
- **Replay semantics**: ND replay now re-executes and may diverge; formalize envelopes before widening backend set.
