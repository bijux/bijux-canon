---
title: Migration Guidance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-20
---

# Migration Guidance

This page is the practical runbook for moving from legacy compatibility package
names to canonical `bijux-canon-*` package names.

Use it when you are actively changing real code, dependency manifests, CI
commands, or deployment configs. If you only need mapping context, start with
[Legacy Name Map](../catalog/legacy-name-map.md).

## Migration Goal

- keep existing environments working during transition
- move all new work to canonical distribution/import/command names
- remove legacy compatibility usage once no known dependents remain

## Canonical Migration Map

| Legacy distribution | Canonical distribution | Canonical import | Canonical command | Canonical package docs |
| --- | --- | --- | --- | --- |
| `agentic-flows` | `bijux-canon-runtime` | `bijux_canon_runtime` | `bijux-canon-runtime` | [Runtime overview](../../06-bijux-canon-runtime/index.md) |
| `bijux-agent` | `bijux-canon-agent` | `bijux_canon_agent` | `bijux-canon-agent` | [Agent overview](../../05-bijux-canon-agent/index.md) |
| `bijux-rag` | `bijux-canon-ingest` | `bijux_canon_ingest` | `bijux-canon-ingest` | [Ingest overview](../../02-bijux-canon-ingest/index.md) |
| `bijux-rar` | `bijux-canon-reason` | `bijux_canon_reason` | `bijux-canon-reason` | [Reason overview](../../04-bijux-canon-reason/index.md) |
| `bijux-vex` | `bijux-canon-index` | `bijux_canon_index` | `bijux-canon-index` | [Index overview](../../03-bijux-canon-index/index.md) |

## Step-By-Step Migration

1. **Replace dependency names** in lockfiles and manifests.
2. **Replace imports** in source and tests.
3. **Replace command invocations** in CI scripts, Make targets, and docs examples.
4. **Run verification** before merging.
5. **Record migration progress** so retirement decisions are evidence-based.

## Dependency Migration

Update package names in files such as:

- `pyproject.toml`
- `requirements*.txt`
- `uv.lock`
- workflow files under `.github/workflows/`

Example replacements:

```text
agentic-flows -> bijux-canon-runtime
bijux-agent   -> bijux-canon-agent
bijux-rag     -> bijux-canon-ingest
bijux-rar     -> bijux-canon-reason
bijux-vex     -> bijux-canon-index
```

## Import Migration

Update Python imports to canonical module names.

Example pattern:

```python
# before
import bijux_rag

# after
import bijux_canon_ingest
```

If compatibility imports still resolve, treat that as temporary continuity,
not a reason to keep new code on legacy names.

## Command Migration

Update command usage in:

- CI jobs
- shell scripts
- Make targets
- runbooks and internal docs

Example pattern:

```bash
# before
bijux-rag --help

# after
bijux-canon-ingest --help
```

## Verification Checklist

Run these checks before merging migration changes:

```bash
# 1) detect remaining legacy dependency/import/command usage
rg -n "agentic-flows|bijux-agent|bijux-rag|bijux-rar|bijux-vex" .

# 2) run repository validation
make check

# 3) confirm docs and examples use canonical names
rg -n "bijux-canon-runtime|bijux-canon-agent|bijux-canon-ingest|bijux-canon-reason|bijux-canon-index" docs packages
```

A migration PR is not complete if step (1) still finds unresolved operational
usage outside explicitly documented compatibility package content.

## Keep vs Retire Decision

Keep a compatibility package only when at least one of these is true:

- there is a known external environment still pinned to the legacy distribution
- a supported integration still requires the legacy command/import surface
- removing it would break a published contract without an agreed deprecation window

Bias toward retirement when:

- no active dependents are identified
- internal code and automation already use canonical names
- compatibility package releases exist only to mirror canonical releases

Use [Retirement Conditions](retirement-conditions.md) and
[Retirement Playbook](retirement-playbook.md) for closure planning.

## Common Failure Modes

- updating docs but not dependency manifests
- updating dependencies but leaving legacy CLI calls in CI
- using compatibility imports in new code “for convenience”
- assuming migration is done without repository-wide search evidence

## Related References

- [Compatibility Overview](compatibility-overview.md)
- [Canonical Targets](canonical-targets.md)
- [Dependency Continuity](dependency-continuity.md)
- [Validation Strategy](validation-strategy.md)
- [Repository Consolidation](repository-consolidation.md)
