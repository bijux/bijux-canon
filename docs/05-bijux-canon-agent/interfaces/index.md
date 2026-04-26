---
title: Interfaces
audience: mixed
type: index
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-04-26
---

# Interfaces

Open this section when the question is what another package, tool, or operator
can safely rely on from `bijux-canon-agent`: commands, HTTP routes, schemas,
config surfaces, orchestration artifacts, trace outputs, and public imports.

This package has unusually high contract pressure because callers do not only
invoke it; they also inspect what it orchestrated. Trace files, result
artifacts, and schema-backed API shapes are part of what readers may depend on
when they assess agent behavior.

## Start Here

- open [CLI Surface](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/cli-surface/) for terminal-facing commands and replay
  entrypoints
- open [API Surface](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/api-surface/) when the contract is HTTP-facing rather
  than CLI-facing
- open [Artifact Contracts](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/artifact-contracts/) and
  [Data Contracts](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/data-contracts/) when trace or result shape matters more
  than invocation syntax

## Pages In This Section

- [CLI Surface](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/cli-surface/)
- [API Surface](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/api-surface/)
- [Configuration Surface](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/configuration-surface/)
- [Data Contracts](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/data-contracts/)
- [Artifact Contracts](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/artifact-contracts/)
- [Entrypoints and Examples](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/entrypoints-and-examples/)
- [Operator Workflows](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/operator-workflows/)
- [Public Imports](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/public-imports/)
- [Compatibility Commitments](https://bijux.io/bijux-canon/05-bijux-canon-agent/interfaces/compatibility-commitments/)

## Open This Section When

- you need to know whether a command, route, trace file, config surface, or
  import is meant to be stable
- a change may affect downstream orchestration expectations or trace readers
- a reviewer needs to separate explicit interfaces from incidental visibility

## Open Another Section When

- the main question is why the behavior belongs in the agent layer at all
- the concern is mostly structural rather than contract-facing
- the issue is procedural or proof-oriented rather than about supported surfaces

## Across This Package

- open [Foundation](https://bijux.io/bijux-canon/05-bijux-canon-agent/foundation/) for package purpose and ownership
- open [Architecture](https://bijux.io/bijux-canon/05-bijux-canon-agent/architecture/) for the structural seams behind
  the public surfaces
- open [Operations](https://bijux.io/bijux-canon/05-bijux-canon-agent/operations/) for setup, diagnostics, and release
  procedures
- open [Quality](https://bijux.io/bijux-canon/05-bijux-canon-agent/quality/) for compatibility evidence and review
  pressure

## Concrete Anchors

- `src/bijux_canon_agent/interfaces/cli/entrypoint.py` for CLI entrypoints
- `src/bijux_canon_agent/api/v1` for HTTP routes and schema-backed handlers
- `src/bijux_canon_agent/config` for operator configuration surfaces
- `src/bijux_canon_agent/traces` and `interfaces/cli/result_artifacts.py` for
  trace and artifact contracts

## Bottom Line

Open this section to judge whether a dependency on the agent layer is
defensible. The bar is not only that a command exists, but that commands,
schemas, traces, artifacts, examples, and tests all agree about what the
orchestration surface really promises.

