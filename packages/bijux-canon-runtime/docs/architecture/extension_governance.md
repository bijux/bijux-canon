# Extension Governance

This document defines how optional or incubating behavior enters `bijux-canon-runtime`
without polluting the stable runtime contract.

## Rules

1. New extension points start behind explicit namespaces or versioned schema fields.
2. Provider-specific behavior stays out of `core/`, `contracts/`, and canonical model types.
3. Optional integrations must prove replay safety before they become default runtime paths.
4. Docs and tests must describe when an extension is opt-in, unstable, or excluded from guarantees.

## What Belongs Here

- Namespacing rules for provider adapters and optional execution hooks.
- Promotion criteria for moving an extension into stable runtime surfaces.
- Guardrails that keep temporary integration code out of the core execution contract.

## What Does Not Belong Here

- Provider implementation details.
- Product roadmaps or speculative feature lists.
- Exceptions that bypass determinism, replay, or audit requirements.
