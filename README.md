# bijux-canon

<!-- bijux-canon-badges:generated:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)
[![Release](https://img.shields.io/github/v/release/bijux/bijux-canon?display_name=tag&label=release)](https://github.com/bijux/bijux-canon/releases)
[![GHCR packages](https://img.shields.io/badge/ghcr-10%20packages-181717?logo=github)](https://github.com/bijux?tab=packages)
[![Published packages](https://img.shields.io/badge/published%20packages-10-2563EB)](https://github.com/bijux/bijux-canon/tree/main/packages)

**PyPI**
[![bijux-canon-runtime](https://img.shields.io/pypi/v/bijux-canon-runtime?label=runtime&logo=pypi)](https://pypi.org/project/bijux-canon-runtime/)
[![bijux-canon-agent](https://img.shields.io/pypi/v/bijux-canon-agent?label=agent&logo=pypi)](https://pypi.org/project/bijux-canon-agent/)
[![bijux-canon-ingest](https://img.shields.io/pypi/v/bijux-canon-ingest?label=ingest&logo=pypi)](https://pypi.org/project/bijux-canon-ingest/)
[![bijux-canon-reason](https://img.shields.io/pypi/v/bijux-canon-reason?label=reason&logo=pypi)](https://pypi.org/project/bijux-canon-reason/)
[![bijux-canon-index](https://img.shields.io/pypi/v/bijux-canon-index?label=index&logo=pypi)](https://pypi.org/project/bijux-canon-index/)
[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows?label=agentic--flows&logo=pypi)](https://pypi.org/project/agentic-flows/)
[![bijux-agent](https://img.shields.io/pypi/v/bijux-agent?label=bijux--agent&logo=pypi)](https://pypi.org/project/bijux-agent/)
[![bijux-rag](https://img.shields.io/pypi/v/bijux-rag?label=bijux--rag&logo=pypi)](https://pypi.org/project/bijux-rag/)
[![bijux-rar](https://img.shields.io/pypi/v/bijux-rar?label=bijux--rar&logo=pypi)](https://pypi.org/project/bijux-rar/)
[![bijux-vex](https://img.shields.io/pypi/v/bijux-vex?label=bijux--vex&logo=pypi)](https://pypi.org/project/bijux-vex/)

**Documentation**
[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-runtime/)
[![bijux-canon-agent docs](https://img.shields.io/badge/docs-agent-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-agent/)
[![bijux-canon-ingest docs](https://img.shields.io/badge/docs-ingest-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-ingest/)
[![bijux-canon-reason docs](https://img.shields.io/badge/docs-reason-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-reason/)
[![bijux-canon-index docs](https://img.shields.io/badge/docs-index-2563EB?logo=materialformkdocs&logoColor=white)](https://bijux.io/bijux-canon/bijux-canon-index/)

**GHCR**
[![bijux-canon-runtime](https://img.shields.io/badge/runtime-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime)
[![bijux-canon-agent](https://img.shields.io/badge/agent-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent)
[![bijux-canon-ingest](https://img.shields.io/badge/ingest-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest)
[![bijux-canon-reason](https://img.shields.io/badge/reason-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason)
[![bijux-canon-index](https://img.shields.io/badge/index-ghcr-181717?logo=github)](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index)
<!-- bijux-canon-badges:generated:end -->

`bijux-canon` is a contract-first Python package family for governed ingest,
retrieval, reasoning, agent execution, and runtime replay.

It exists for teams that need more than "it worked once on my machine." The
goal is not just to run AI and retrieval workflows, but to run them with clear
boundaries, stable contracts, checked-in schemas, replayable behavior, and a
repository layout that stays understandable as the system grows.

This repository publishes `10` packages. Each release tag builds one staged
bundle per package, uploads distributions to PyPI, publishes release bundles to
`ghcr.io/bijux/bijux-canon/<package>`, and attaches the same staged assets to
the GitHub Release.

## Why `bijux-canon` Exists

Many AI and RAG stacks are easy to start and hard to trust. They often mix
ingest, indexing, reasoning, orchestration, and runtime policy in one blurred
layer. That makes systems harder to review, migrate, test, replay, and operate.

`bijux-canon` fills that gap by treating these concerns as separate but aligned
layers:

- `ingest` prepares and shapes information
- `index` executes retrieval contracts
- `reason` manages reasoning-side state and run artifacts
- `agent` orchestrates deterministic agent workflows
- `runtime` enforces execution and replay policy above the rest

The result is a stack that is easier to govern, easier to inspect, and easier
to evolve without losing the plot.

## Repository Consolidation

The package family now ships from a single repository:

- canonical repository: <https://github.com/bijux/bijux-canon>
- migration handbook: <https://bijux.io/bijux-canon/compat-packages/migration/migration-guidance/>
- repository consolidation notes: <https://bijux.io/bijux-canon/compat-packages/migration/repository-consolidation/>

The following standalone repositories are being retired in favor of the
consolidated `bijux-canon` source of truth:

- `https://github.com/bijux/agentic-flows` -> `bijux-canon-runtime`
- `https://github.com/bijux/bijux-agent` -> `bijux-canon-agent`
- `https://github.com/bijux/bijux-rag` -> `bijux-canon-ingest`
- `https://github.com/bijux/bijux-rar` -> `bijux-canon-reason`
- `https://github.com/bijux/bijux-vex` -> `bijux-canon-index`

## What Makes It Different

- Contracts are first-class. API schemas are checked in under `apis/` instead of
  being an afterthought.
- Determinism matters. The system is built around bounded execution, traceable
  behavior, and replay where it matters.
- Layers stay legible. Each package owns a specific slice of responsibility
  instead of collapsing into one "do everything" library.
- Compatibility is explicit. Legacy package names are preserved through compat
  packages instead of being hidden or silently broken.
- The repository is designed as one system. Docs, schemas, validation, release
  flow, and automation are meant to stay aligned.

## Package Map

The 10 publishable packages in this repository are:

| Package | Purpose | Links |
| --- | --- | --- |
| `bijux-canon-runtime` | Governed execution, policy enforcement, and replay | [PyPI](https://pypi.org/project/bijux-canon-runtime/) [Docs](https://bijux.io/bijux-canon/bijux-canon-runtime/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-runtime) [`source`](packages/bijux-canon-runtime) |
| `bijux-canon-agent` | Deterministic agent orchestration and execution surfaces | [PyPI](https://pypi.org/project/bijux-canon-agent/) [Docs](https://bijux.io/bijux-canon/bijux-canon-agent/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-agent) [`source`](packages/bijux-canon-agent) |
| `bijux-canon-ingest` | Deterministic ingest, chunking, indexing, and retrieval preparation | [PyPI](https://pypi.org/project/bijux-canon-ingest/) [Docs](https://bijux.io/bijux-canon/bijux-canon-ingest/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-ingest) [`source`](packages/bijux-canon-ingest) |
| `bijux-canon-reason` | Contract-driven reasoning runtime and run artifacts | [PyPI](https://pypi.org/project/bijux-canon-reason/) [Docs](https://bijux.io/bijux-canon/bijux-canon-reason/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-reason) [`source`](packages/bijux-canon-reason) |
| `bijux-canon-index` | Contract-driven vector execution and audited retrieval | [PyPI](https://pypi.org/project/bijux-canon-index/) [Docs](https://bijux.io/bijux-canon/bijux-canon-index/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-canon-index) [`source`](packages/bijux-canon-index) |
| `agentic-flows` | Compatibility package for `bijux-canon-runtime` | [PyPI](https://pypi.org/project/agentic-flows/) [Docs](https://bijux.io/bijux-canon/compat-packages/catalog/agentic-flows/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fagentic-flows) [`source`](packages/compat-agentic-flows) |
| `bijux-agent` | Compatibility package for `bijux-canon-agent` | [PyPI](https://pypi.org/project/bijux-agent/) [Docs](https://bijux.io/bijux-canon/compat-packages/catalog/bijux-agent/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-agent) [`source`](packages/compat-bijux-agent) |
| `bijux-rag` | Compatibility package for `bijux-canon-ingest` | [PyPI](https://pypi.org/project/bijux-rag/) [Docs](https://bijux.io/bijux-canon/compat-packages/catalog/bijux-rag/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rag) [`source`](packages/compat-bijux-rag) |
| `bijux-rar` | Compatibility package for `bijux-canon-reason` | [PyPI](https://pypi.org/project/bijux-rar/) [Docs](https://bijux.io/bijux-canon/compat-packages/catalog/bijux-rar/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-rar) [`source`](packages/compat-bijux-rar) |
| `bijux-vex` | Compatibility package for `bijux-canon-index` | [PyPI](https://pypi.org/project/bijux-vex/) [Docs](https://bijux.io/bijux-canon/compat-packages/catalog/bijux-vex/) [GHCR](https://github.com/bijux/bijux-canon/pkgs/container/bijux-canon%2Fbijux-vex) [`source`](packages/compat-bijux-vex) |

Repository-owned developer tooling also lives here in
[`packages/bijux-canon-dev`](packages/bijux-canon-dev), but it is for
maintaining the workspace rather than for end-user installation.

## Choose Your Entry Point

- Start with `bijux-canon-runtime` if you care about governed execution, policy,
  replay, and system-level control.
- Start with `bijux-canon-agent` if you need agent orchestration and
  deterministic workflow execution.
- Start with `bijux-canon-ingest` if your main problem is preparing, chunking,
  and shaping source material for downstream use.
- Start with `bijux-canon-reason` if you need a reasoning-side runtime with
  explicit run artifacts and state boundaries.
- Start with `bijux-canon-index` if retrieval and vector execution are the main
  concern.

## Documentation Paths

- Repository handbook: <https://bijux.io/bijux-canon/>
- Repository handbook source: [`docs/index.md`](docs/index.md)
- Repository overview section: [`docs/bijux-canon`](docs/bijux-canon)
- Compatibility handbook: [`docs/compat-packages`](docs/compat-packages)
- Maintenance handbook: [`docs/bijux-canon-maintain`](docs/bijux-canon-maintain)

If you want the fastest high-level orientation, start with the repository
handbook and then jump to the package docs that match the layer you care about.

## Where `bijux-canon` Fits

`bijux-canon` is not trying to be the most magical framework in the room. It is
trying to be one of the clearest.

Its place in the community is the gap between:

- quick demos that are easy to start but hard to trust later
- heavyweight enterprise systems that bury the actual execution model under too
  much machinery

`bijux-canon` is for people who want explicit boundaries, honest contracts,
clear artifacts, and a codebase that still makes sense after the first demo.

## Start Here

- Want the whole picture: read [`docs/index.md`](docs/index.md)
- Want package-level entry points: browse [`packages/`](packages)
- Want checked-in API contracts: browse [`apis/`](apis)
- Want workspace automation: run `make help`
- Want to build the handbook locally: run `make docs-check` or `make docs-serve`
- Want contributor guidance: read [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Repository Design

The root keeps only the assets that truly need repository ownership:

- `apis/` for checked-in contract artifacts
- `configs/` for shared tool configuration
- `docs/` for the root handbook
- `makes/` for automation and orchestration
- `.github/workflows/` for CI and release flow
- `packages/` for the publishable distributions

That split is intentional. It keeps package code local, shared governance
visible, and repository policy discoverable for both human readers and tooling.
