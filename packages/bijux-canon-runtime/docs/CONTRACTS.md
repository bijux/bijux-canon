# Contracts

The runtime contract surface matters across packages because replay and audit
depend on it.

## Stable surfaces

- console script `bijux-canon-runtime`
- API surface and schema artifacts under `apis/06-bijux-canon-runtime/v1/`
- runtime models under `model/`
- CLI behavior under `interfaces/cli/`
- execution-store schema artifacts and migrations

## Change policy

Runtime contract changes should be explicit because they affect replay,
auditability, and package interaction across the system.
