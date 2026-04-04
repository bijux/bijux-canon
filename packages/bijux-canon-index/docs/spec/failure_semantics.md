# Failure Semantics

Failures in `bijux-canon-index` are part of the contract surface.

The package distinguishes between:
- validation failures: the request shape or declared contract is invalid
- invariant failures: internal or cross-layer guarantees were violated
- capability failures: the selected backend, vector store, or plugin cannot satisfy the request
- budget failures: configured latency, memory, or approximation limits were exceeded
- replay failures: a replay request cannot be honored under the declared reproducibility constraints

Boundary layers must preserve these meanings:
- CLI maps typed failures to stable exit codes
- HTTP maps typed failures to stable status codes and refusal payloads
- run records store failure details without inventing new categories

New failure types should only be introduced when they add a durable distinction that downstream tooling can act on.
