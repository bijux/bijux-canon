# Runtime Scope

Bijux Canon Runtime exists to resolve manifests into governed execution plans, run
those plans under explicit determinism rules, and preserve enough evidence to replay
or audit the result later.

## Primary Responsibilities

- Turn a manifest into a stable execution plan.
- Execute that plan under deterministic, observed, or unsafe modes with explicit intent.
- Persist traces, artifacts, evidence, and replay metadata.
- Offer CLI and API surfaces that reflect the same runtime contract.

## Non-Goals

- A chat-first application surface.
- A general workflow authoring package.
- Domain-specific retrieval or indexing logic.
- Provider-specific behavior baked into core runtime models.
