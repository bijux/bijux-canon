# CONTRACTS

Stable contracts in `bijux-canon-runtime` are:
- console script `bijux-canon-runtime`
- API surface and schema artifacts under `apis/bijux-canon-runtime/v1/`
- runtime models under `src/bijux_canon_runtime/model/`
- CLI behavior under `src/bijux_canon_runtime/interfaces/cli/`
- execution-store schema artifacts under `src/bijux_canon_runtime/observability/`

Runtime contract changes should be explicit because they affect replay and audit guarantees across packages.
