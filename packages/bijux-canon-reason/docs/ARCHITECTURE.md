# ARCHITECTURE

`bijux-canon-reason` is a deterministic reasoning package.

Core layout:
- `src/bijux_canon_reason/core/models/` owns durable reasoning, claim, trace, and verification models
- `src/bijux_canon_reason/planning/`, `reasoning/`, and `verification/` own reasoning flow and validation semantics
- `src/bijux_canon_reason/execution/` owns step execution and tool dispatch
- `src/bijux_canon_reason/interfaces/cli/` and `api/v1/` own external boundaries

The architecture should keep reasoning and verification semantics separate from CLI/API transport code.
