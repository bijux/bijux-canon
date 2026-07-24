---
title: Preserved Name Map
audience: mixed
type: reference
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-07-21
---

# Preserved Name Map

Use this map when an existing dependency, import, module path, or executable
uses a non-canonical identity.

## Distribution And Root Import

| Encountered identity | Kind | Canonical distribution | Canonical import |
| --- | --- | --- | --- |
| `bijux-canon` | shorter runtime distribution | `bijux-canon-runtime` | `bijux_canon_runtime` |
| `bijux_canon` | shorter runtime import | `bijux-canon-runtime` | `bijux_canon_runtime` |
| `agentic-flows` | earlier runtime distribution | `bijux-canon-runtime` | `bijux_canon_runtime` |
| `agentic_flows` | earlier runtime import | `bijux-canon-runtime` | `bijux_canon_runtime` |
| `bijux-agent` / `bijux_agent` | agent distribution / import | `bijux-canon-agent` | `bijux_canon_agent` |
| `bijux-rag` / `bijux_rag` | ingest distribution / import | `bijux-canon-ingest` | `bijux_canon_ingest` |
| `bijux-rar` / `bijux_rar` | reason distribution / import | `bijux-canon-reason` | `bijux_canon_reason` |
| `bijux-vex` / `bijux_vex` | index distribution / import | `bijux-canon-index` | `bijux_canon_index` |

## Executables

| Existing executable | Canonical replacement |
| --- | --- |
| `bijux-canon` | `bijux-canon-runtime` |
| `agentic-flows` | `bijux-canon-runtime` |
| `bijux-agent` | `bijux-canon-agent` |
| `bijux-rag` | `bijux-canon-ingest` |
| `bijux-rar` | `bijux-canon-reason` |
| `bijux-vex` | no direct executable; migrate to `bijux-canon-index` Python or HTTP contracts |

## Nested Imports

The bridges install import finders that translate non-local nested paths. For
example, `bijux_rag.core.types` resolves to the canonical
`bijux_canon_ingest.core.types` module object, and `bijux_vex.core.runtime`
resolves through the index module tree. The bridge retains local ownership only
for its alias machinery and `__main__` surface.

Identity tests cover representative root, CLI, and nested paths for each
bridge. Migrate all imported submodules explicitly even when the compatibility
finder makes them continue to work; arbitrary private paths are not a broader
compatibility guarantee.

## Where Current Behavior Lives

| Owner | Handbook |
| --- | --- |
| `bijux-canon-runtime` | [Runtime](../../06-bijux-canon-runtime/index.md) |
| `bijux-canon-agent` | [Agent](../../05-bijux-canon-agent/index.md) |
| `bijux-canon-ingest` | [Ingest](../../02-bijux-canon-ingest/index.md) |
| `bijux-canon-reason` | [Reason](../../04-bijux-canon-reason/index.md) |
| `bijux-canon-index` | [Index](../../03-bijux-canon-index/index.md) |

Continue with [package behavior](package-behavior.md) for bridge mechanics or
[migration guidance](../migration/migration-guidance.md) for a complete
dependency, import, command, configuration, and artifact inventory.
