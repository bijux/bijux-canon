# bijux-canon

`bijux-canon` is the monorepo for the Bijux Canon package family. It keeps the
runtime, agent, ingest, reasoning, indexing, compatibility, and repository
tooling layers in one governed workspace so shared contracts can evolve
together instead of drifting across separate repositories.

## What Lives Here

The repository owns two kinds of things:

- publishable Python distributions under `packages/`
- repository-level assets that must stay above any single package

The root is intentionally small. If something belongs to one package, it stays
with that package. If something governs the whole workspace, it lives here.

## Package Map

| Package | Role |
| --- | --- |
| `bijux-canon-runtime` | Contract-enforced execution and replay for the runtime layer |
| `bijux-canon-agent` | Deterministic agent orchestration and execution surfaces |
| `bijux-canon-ingest` | Deterministic ingest, chunking, indexing, and retrieval preparation |
| `bijux-canon-reason` | Reasoning runtime and auditable run management |
| `bijux-canon-index` | Contract-driven vector execution and retrieval |
| `bijux-canon-dev` | Repository-owned developer tooling for docs and workspace automation |
| `compat-*` packages | Compatibility shims for legacy package names and migration paths |

## Repository Layout

- `apis/` contains checked-in API contracts, pinned OpenAPI artifacts, and hash
  files for the publishable package surfaces.
- `configs/` contains shared tool configuration for linting, typing, testing,
  dependency auditing, and schema validation.
- `docs/` contains the repository handbook and the reader-facing overview of the
  whole Bijux Canon system.
- `makes/` is the single source of truth for root and package automation.
- `packages/` contains every publishable distribution and the repository-owned
  developer tooling package.
- `.github/workflows/` contains repository CI and publish orchestration.

## Working Model

- package runtime code stays inside the owning package
- repository policy, governance, and shared automation stay at the root
- generated outputs belong under `artifacts/`
- compatibility packages exist to ease migration, not to define the future
  architecture

This split matters because the repository is meant to behave like one designed
system, even though it publishes multiple packages.

## Common Entry Points

- read [docs/index.md](docs/index.md) for the root handbook
- read [CONTRIBUTING.md](CONTRIBUTING.md) before changing repository-wide
  behavior
- read [SECURITY.md](SECURITY.md) for vulnerability reporting
- run `make help` for the generated root command list
- run `make docs-check` to validate the root handbook build

## History and Compatibility

Some package import paths and compatibility distributions preserve older Bijux
names while the repository converges on the `bijux-canon-*` family. That
history is documented in the compatibility handbook and in
`docs/repository-history.md`.
