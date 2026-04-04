# Scope

`bijux-canon-reason` exists to model and execute reasoning workflows with
explicit verification, structured claims, and evidence-aware behavior.

## In scope

- reasoning plan and claim modeling
- planning and execution of reasoning steps
- verification rules and provenance checks that belong to reasoning itself
- package-local CLI and API access

## Out of scope

- runtime storage, governance, and replay authority
- ingest and vector index ownership
- monorepo tooling concerns

## Rule of thumb

If the question is "how should the system reason, justify, and verify this
answer," the change likely belongs here.
