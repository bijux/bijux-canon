# Boundaries

`bijux-canon-agent` sits between callers on one side and deeper domain packages
or runtime governance on the other.

## This package owns

- local agent orchestration and lifecycle control
- trace-backed execution records that explain what the agent package did
- package-local CLI and HTTP request handling
- final result assembly that is specific to the agent package's workflow

## Neighbor packages own

- `bijux-canon-runtime`: persistence, replay policy, and execution authority
- `bijux-canon-ingest`: document preparation and ingest-local retrieval assembly
- `bijux-canon-index`: vector execution and replay-aware index behavior
- `bijux-canon-reason`: reasoning, claims, and verification semantics

## Boundary discipline

- do not move runtime governance into agent helpers
- do not hide domain-specific reasoning or indexing logic inside the pipeline
- do not let interface code accumulate orchestration policy that belongs in application or pipeline code
