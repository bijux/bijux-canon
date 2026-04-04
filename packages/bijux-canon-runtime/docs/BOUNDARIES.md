# Boundaries

`bijux-canon-runtime` owns the authority layer. Other packages may define what a
step means, but runtime decides how governed execution and replay behave.

## This package owns

- runtime authority and replay semantics
- trace capture and execution-store behavior
- operator CLI and API boundaries for runtime flows
- non-determinism accounting and policy enforcement

## Neighbor packages own

- `bijux-canon-agent`: agent composition policy
- `bijux-canon-ingest` and `bijux-canon-index`: their own domain semantics
- `bijux-canon-dev`: repository tooling

## Boundary discipline

- do not move authority decisions into domain packages
- do not let transport code become the real home of runtime policy
- do not weaken replay semantics by hiding important execution details outside runtime
