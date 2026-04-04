# bijux-canon-agent

`bijux-canon-agent` is the package that turns a declared agent workflow into a
deterministic, inspectable execution. It is where role implementations,
pipeline coordination, trace production, and package-local operator surfaces
come together.

If you need to understand how an agent run is composed, how trace-backed output
is produced, or where agent-facing CLI and HTTP behavior lives, start here. If
you need replay governance, runtime persistence, or cross-package execution
authority, you are probably looking for `bijux-canon-runtime` instead.

## What this package owns

- agent role implementations and the helpers that are specific to those roles
- deterministic orchestration of the local agent pipeline
- trace-backed result artifacts that explain what happened during a run
- package-local CLI and HTTP boundaries for invoking agent workflows

## What this package does not own

- runtime-wide persistence, replay acceptance, or execution governance
- ingest and index engines that belong to other package boundaries
- repository tooling, release automation, or root-level quality workflows

## Source map

- [`src/bijux_canon_agent/agents`](src/bijux_canon_agent/agents) for role-local behavior
- [`src/bijux_canon_agent/pipeline`](src/bijux_canon_agent/pipeline) for execution flow
- [`src/bijux_canon_agent/application`](src/bijux_canon_agent/application) for orchestration policies
- [`src/bijux_canon_agent/interfaces`](src/bijux_canon_agent/interfaces) for CLI and HTTP edges
- [`src/bijux_canon_agent/traces`](src/bijux_canon_agent/traces) for durable trace-facing models
- [`tests`](tests) for executable package truth

## Read this next

- [Package guide](docs/index.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Boundaries](docs/BOUNDARIES.md)
- [Contracts](docs/CONTRACTS.md)
- [Tests](docs/TESTS.md)

## Primary entrypoint

- console script: `bijux-canon-agent`
