---
title: Migration Guidance
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-07-21
---

# Migration Guidance

Migrate a compatibility identity as a set of observable surfaces: dependency,
root and nested imports, executable invocations, module execution,
configuration, stored artifacts, container references, and operational notes.
Changing only the dependency name can leave the running system on compatibility
imports or commands.

## Target Matrix

| From | Canonical distribution | Canonical import | Canonical executable |
| --- | --- | --- | --- |
| `bijux-canon` | `bijux-canon-runtime` | `bijux_canon_runtime` | `bijux-canon-runtime` |
| `agentic-flows` | `bijux-canon-runtime` | `bijux_canon_runtime` | `bijux-canon-runtime` |
| `bijux-agent` | `bijux-canon-agent` | `bijux_canon_agent` | `bijux-canon-agent` |
| `bijux-rag` | `bijux-canon-ingest` | `bijux_canon_ingest` | `bijux-canon-ingest` |
| `bijux-rar` | `bijux-canon-reason` | `bijux_canon_reason` | `bijux-canon-reason` |
| `bijux-vex` | `bijux-canon-index` | `bijux_canon_index` | none; replace command integration with Python or HTTP |

## Inventory Before Editing

Search dependency and executable spellings separately from Python imports. Exclude
the compatibility packages and their handbook when auditing this repository,
because those paths intentionally retain the preserved identities.

```bash
rg -n 'agentic-flows|bijux-agent|bijux-rag|bijux-rar|bijux-vex' \
  --glob '!packages/compat-*/**' \
  --glob '!docs/08-compat-packages/**'

rg -n 'agentic_flows|bijux_agent|bijux_rag|bijux_rar|bijux_vex' \
  --glob '!packages/compat-*/**' \
  --glob '!docs/08-compat-packages/**'
```

Audit the shorter `bijux-canon` / `bijux_canon` runtime identity manually or
with path-specific searches because those strings are prefixes of canonical
family names. Record each hit by surface and owner rather than applying a blind
repository-wide replacement.

## Migrate In Reviewable Units

1. Replace the dependency and regenerate the lock file with the project's
   normal package manager.
2. Replace root and nested imports; run the narrow tests that exercise the
   imported types and behavior.
3. Replace console and `python -m` invocations. For `bijux-vex`, redesign the
   call against index's typed Python or HTTP contract.
4. Move environment variables, configuration keys, image references, and
   artifact readers only where the canonical owner defines a replacement.
5. Update operational examples and deployment manifests.
6. Remove the compatibility dependency after all runtime environments use the
   canonical identity.
7. Run focused canonical tests and the consumer's integration tests.

Keeping these units separate makes a failure attributable. If imports pass but
artifact reading fails, the bridge can remain while the artifact boundary is
corrected without restoring old imports.

## Direct Rename Example

For `bijux-rag`, dependency, import, and command surfaces have direct targets:

```toml
# pyproject.toml
dependencies = ["bijux-canon-ingest"]
```

```python
from bijux_canon_ingest import RawDoc
```

```bash
bijux-canon-ingest --help
```

Verify the actual ingest operation used by the consumer; `--help` proves only
that the new executable resolves.

## Index Command Migration

Do not perform this replacement:

```text
bijux-vex -> bijux-canon-index
```

There is no canonical executable with that name. Identify which `bijux-vex`
operation the automation uses, map its request and output to the index Python or
HTTP contract, and add an integration test at that boundary. Keep the bridge
installed until the replacement is deployed everywhere that invokes the old
command.

## Completion Evidence

A migration record should identify:

- the dependency and lock changes;
- the removed import and command hits;
- configuration, container, and artifact-reader changes;
- focused canonical and consumer test results;
- remaining bridge-dependent environments, if any; and
- the earliest safe removal point for the compatibility dependency.

Run the consumer's narrow validation first. Use repository-wide checks only
when shared metadata or cross-package contracts changed. Successful installation
alone does not prove import identity, command behavior, or artifact continuity.

Continue with [validation strategy](validation-strategy.md) for parity evidence
and [retirement conditions](retirement-conditions.md) before removing a
published bridge.
