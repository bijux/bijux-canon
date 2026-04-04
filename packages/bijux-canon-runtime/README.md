# bijux-canon-runtime

`bijux-canon-runtime` is the package that decides whether and how a flow runs,
what gets recorded about that run, and how a later replay should be judged. It
is the authority layer for execution, replay, runtime persistence, and
non-determinism governance.

If you need to understand plan versus run modes, replay acceptance, trace
capture, execution-store behavior, or non-determinism policy enforcement, start
here.

## What this package owns

- flow execution authority
- replay and acceptability semantics
- trace capture, runtime persistence, and execution-store behavior
- package-local CLI and API boundaries

## What this package does not own

- agent composition policy
- ingest or index domain ownership
- repository tooling and release support

## Source map

- [`src/bijux_canon_runtime/model`](src/bijux_canon_runtime/model) for durable runtime models
- [`src/bijux_canon_runtime/runtime`](src/bijux_canon_runtime/runtime) for execution engines and lifecycle logic
- [`src/bijux_canon_runtime/application`](src/bijux_canon_runtime/application) for orchestration and replay coordination
- [`src/bijux_canon_runtime/observability`](src/bijux_canon_runtime/observability) for trace capture, analysis, and storage support
- [`src/bijux_canon_runtime/interfaces`](src/bijux_canon_runtime/interfaces) and [`src/bijux_canon_runtime/api`](src/bijux_canon_runtime/api) for boundaries
- [`tests`](tests) and [`examples`](examples) for executable expectations and teaching material

## Read this next

- [Package guide](docs/index.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Boundaries](docs/BOUNDARIES.md)
- [Contracts](docs/CONTRACTS.md)
- [Tests](docs/TESTS.md)

## Primary entrypoint

- console script: `bijux-canon-runtime`
