---
title: Dependency Continuity
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-07-21
---

# Dependency Continuity

A compatibility wheel at version `X` requires its canonical distribution at
exactly `X`. This is the central installation invariant: preserved imports and
commands execute against the canonical release whose surface the bridge was
built and tested to delegate.

## Exact-Pin Contract

| Compatibility distribution | Canonical requirement in built metadata |
| --- | --- |
| `bijux-canon` | `bijux-canon-runtime==X` |
| `agentic-flows` | `bijux-canon-runtime==X` |
| `bijux-agent` | `bijux-canon-agent==X` |
| `bijux-rag` | `bijux-canon-ingest==X` |
| `bijux-rar` | `bijux-canon-reason==X` |
| `bijux-vex` | `bijux-canon-index==X` |

```mermaid
flowchart LR
    request["install bridge X"]
    wheel["bridge wheel metadata"]
    pin["canonical owner == X"]
    graph{"dependency graph agrees?"}
    pair["install tested pair"]
    conflict["resolver conflict"]

    request --> wheel --> pin --> graph
    graph -->|"yes"| pair
    graph -->|"no"| conflict
```

The source `pyproject.toml` does not contain this requirement as a literal
dependency list. Each package's Hatch metadata hook receives the VCS-derived
version and injects the exact canonical requirement into wheel and source
archive metadata. Inspect a built artifact when validating the final graph.

## Resolve Conflicts Deliberately

| Installed or requested state | Meaning | Safe decision |
| --- | --- | --- |
| bridge `X`, no canonical owner | resolver installs canonical `X` | retain both artifacts in the lockfile |
| bridge `X`, canonical `X` | aligned compatibility pair | validate the consumer's used surfaces |
| bridge `X`, canonical `Y` | incompatible graph | align versions or remove the bridge through migration |
| two bridges at `X` targeting runtime `X` | compatible shared owner | validate both preserved roots and commands |
| two bridges at different versions targeting runtime | incompatible exact pins | align both bridges or migrate one before resolving |
| canonical owner only | compatibility name no longer installed | confirm no preserved import, command, plugin, or recovery path remains |

Do not loosen the bridge dependency to a version range to silence the solver.
That would allow alias code built for one release to attach to an unvalidated
canonical surface and would make failures dependent on resolver choice.

## Source Workspace Versus Published Install

The repository workspace maps every canonical and compatibility distribution
to local sources. That is useful for development, but it can hide publication
and packaging defects:

- a local source tree exists even when the corresponding wheel was never
  uploaded;
- editable or workspace resolution can bypass the exact artifacts selected by
  a production lockfile;
- imports can succeed from a checkout even when wheel contents or metadata are
  incomplete; and
- a console entrypoint can be visible through another installed distribution.

Validate continuity from built wheels in an isolated environment before
claiming a release is usable. Record the bridge wheel hash, canonical wheel
hash, selected index, Python version, and resolver output.

## Installed-State Checks

```bash
python -m pip show bijux-rag bijux-canon-ingest
python -m pip check
python -c "import bijux_rag, bijux_canon_ingest; print(bijux_rag.__version__)"
bijux-rag --help
```

Replace the example pair and command with the consumer's bridge. Then exercise
at least one representative nested import and expected failure path. Version
alignment alone cannot prove that import identity, command dispatch, or error
propagation is intact.

For reproducible environments, retain lockfile records and artifact hashes for
both distributions. A lock update is migration evidence because it exposes
transitive changes beyond the intended pair.

## What the Pin Does Not Establish

An exact pin does not prove:

- that both artifacts are available from the selected package index;
- that the installed files match repository source;
- that private nested imports remain supported;
- that command automation still uses the intended executable;
- that caches or stored artifacts carry compatible schema and identity; or
- that a consumer has completed migration.

Use [release policy](release-policy.md) to establish artifact availability and
[validation strategy](validation-strategy.md) to prove installed delegation.
Historical data still requires the canonical owner's artifact compatibility
checks.
