---
title: Canonical Targets
audience: mixed
type: reference
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-07-21
---

# Canonical Targets

Every compatibility distribution has one canonical owner. Migration changes
the distribution, Python import, and—where available—console command as separate
observable surfaces.

## Exact Target Map

| Preserved distribution | Preserved import | Preserved command | Canonical distribution | Canonical import | Canonical command | Handbook |
| --- | --- | --- | --- | --- | --- | --- |
| `bijux-canon` | `bijux_canon` | `bijux-canon` | `bijux-canon-runtime` | `bijux_canon_runtime` | `bijux-canon-runtime` | [Runtime](../../06-bijux-canon-runtime/index.md) |
| `agentic-flows` | `agentic_flows` | `agentic-flows` | `bijux-canon-runtime` | `bijux_canon_runtime` | `bijux-canon-runtime` | [Runtime](../../06-bijux-canon-runtime/index.md) |
| `bijux-agent` | `bijux_agent` | `bijux-agent` | `bijux-canon-agent` | `bijux_canon_agent` | `bijux-canon-agent` | [Agent](../../05-bijux-canon-agent/index.md) |
| `bijux-rag` | `bijux_rag` | `bijux-rag` | `bijux-canon-ingest` | `bijux_canon_ingest` | `bijux-canon-ingest` | [Ingest](../../02-bijux-canon-ingest/index.md) |
| `bijux-rar` | `bijux_rar` | `bijux-rar` | `bijux-canon-reason` | `bijux_canon_reason` | `bijux-canon-reason` | [Reason](../../04-bijux-canon-reason/index.md) |
| `bijux-vex` | `bijux_vex` | `bijux-vex` | `bijux-canon-index` | `bijux_canon_index` | none | [Index](../../03-bijux-canon-index/index.md) |

## Command Asymmetry

The first five rows have direct canonical command replacements. Index does not:
the `bijux-canon-index` distribution intentionally has no `[project.scripts]`
entry, while `bijux-vex` registers its preserved command against the canonical
Typer application.

Do not replace `bijux-vex` with an invented `bijux-canon-index` executable.
Migrate the operation to index's typed Python API or versioned HTTP contract,
then remove the compatibility command from automation.

## Dependency Contract

Compatibility dependencies are generated at build time. Each bridge resolves
its own SCM version and writes an exact dependency of the form:

```text
canonical-distribution==resolved-bridge-version
```

This prevents a compatibility wheel from silently selecting a different
canonical release. It does not prove behavioral parity by itself; import
identity, command delegation, package tests, and release artifact checks provide
the remaining evidence.

## Targeting Rules

- New dependency declarations use the canonical distribution.
- New Python code imports the canonical module root.
- New command automation uses a canonical command only when the canonical
  distribution publishes one.
- Artifact and configuration migrations follow the owning package's current
  contracts rather than performing a blind string replacement.
- Compatibility code contains delegation machinery only; product changes land
  in the canonical owner.

Use the [legacy name map](../catalog/legacy-name-map.md) when starting from an
import or executable name, and [migration guidance](migration-guidance.md) when
inventorying a real codebase.
