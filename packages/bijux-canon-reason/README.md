# bijux-canon-reason

`bijux-canon-reason` is the package that turns available evidence into planned
reasoning steps, structured claims, and verification outcomes. It is where
reasoning behavior is made explicit enough to inspect, test, and defend.

If you need to understand how claims are formed, how reasoning steps are
planned and executed, how evidence is used, or where verification lives, start
here. If you need runtime governance, storage, or vector execution internals,
you are outside this package's boundary.

## What this package owns

- reasoning plans, claims, and evidence-aware reasoning models
- execution of reasoning steps and local tool dispatch
- verification and provenance checks that belong to reasoning itself
- package-local CLI and API boundaries

## What this package does not own

- runtime persistence, replay authority, or execution governance
- ingest and index engines
- repository tooling and release automation

## Source map

- [`src/bijux_canon_reason/planning`](src/bijux_canon_reason/planning) for planning behavior
- [`src/bijux_canon_reason/reasoning`](src/bijux_canon_reason/reasoning) for claim and reasoning semantics
- [`src/bijux_canon_reason/execution`](src/bijux_canon_reason/execution) for step execution
- [`src/bijux_canon_reason/verification`](src/bijux_canon_reason/verification) for checks and outcomes
- [`src/bijux_canon_reason/interfaces`](src/bijux_canon_reason/interfaces) and [`src/bijux_canon_reason/api`](src/bijux_canon_reason/api) for boundaries
- [`tests`](tests) for executable protection of the package contract

## Read this next

- [Package guide](docs/index.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Contracts](docs/CONTRACTS.md)
- [Tests](docs/TESTS.md)
- [Changelog](CHANGELOG.md)
