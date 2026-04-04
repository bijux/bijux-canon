# Scope

`bijux-canon-runtime` exists to execute governed flows, record what happened,
and decide how replay should be interpreted later.

## In scope

- flow resolution and execution coordination
- replay analysis and acceptability checks
- runtime persistence and trace capture
- package-local CLI and API access

## Out of scope

- agent authoring policy
- ingest and index domain ownership
- monorepo tooling and release support

## Rule of thumb

If the question is "who is allowed to run this, how is it recorded, and what
counts as an acceptable replay," the change likely belongs here.
