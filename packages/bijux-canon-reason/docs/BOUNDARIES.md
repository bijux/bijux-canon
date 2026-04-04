# Boundaries

`bijux-canon-reason` owns the reasoning story, not the whole runtime story.

## This package owns

- planning and execution of reasoning steps
- claim formation and evidence-aware reasoning behavior
- verification and provenance checks local to reasoning
- reasoning-facing HTTP and CLI boundaries

## Neighbor packages own

- `bijux-canon-runtime`: persistence, replay policy, and execution governance
- `bijux-canon-ingest` and `bijux-canon-index`: ingest and index execution internals
- `bijux-canon-dev`: repository tooling

## Boundary discipline

- do not push runtime authority into reasoning helpers
- do not absorb ingest or vector-engine internals just because reasoning depends on them
- do not let interface code become the real home of reasoning policy
