# Project Tree & Guide

Quick map of the `bijux-canon-ingest` package directory.

## Package Layout

```text
.
├── docs/                          # package docs, ADRs, and reference pages
├── src/bijux_canon_ingest/        # library code
│   ├── application/               # orchestration surfaces
│   ├── config/                    # configuration models and builders
│   ├── core/                      # core types, rules, and dedup helpers
│   ├── domain/                    # effect descriptions and domain capabilities
│   ├── fp/                        # functional helper internals
│   ├── infra/                     # runtime adapters
│   ├── interfaces/                # cli, http, serialization, and error boundaries
│   ├── interop/                   # compatibility helpers
│   ├── policies/                  # reusable cross-cutting behaviors
│   ├── processing/                # pure ingest transforms
│   ├── result/                    # result and option helpers
│   ├── retrieval/                 # indexing, retrieval, reranking, answering
│   ├── streaming/                 # streaming helpers
│   └── tree/                      # tree traversal and folds
├── stubs/                         # custom typing stubs
├── tests/                         # unit, e2e, eval assets, and helpers
├── CHANGELOG.md                   # version history
├── Makefile                       # package automation entrypoint
├── mkdocs.yml                     # package-owned docs config
└── pyproject.toml                 # build metadata and dependencies
```

## Source Code

- `application/` keeps orchestration readable by splitting responsibilities into `indexing`, `querying`, `service`, `pipeline`, and `pipelines`.
- `interfaces/` holds adapter code that should not leak into the core model: CLI, HTTP, serialization, and error mapping.
- `processing/`, `core/`, `retrieval/`, and `domain/` hold the main ingest and retrieval logic.
- `fp/`, `result/`, `streaming/`, `tree/`, `interop/`, and `policies/` support the package internally without pretending to be separate apps.

## Tests & Eval

- `tests/unit/` covers application, interfaces, processing, retrieval, domain, infra, fp, result, streaming, and tree behavior.
- `tests/e2e/` covers CLI and end-to-end retrieval flows.
- `tests/eval/` stores pinned corpus and query fixtures for evaluation gates.

## Config & Tooling

- `Makefile` drives package-local targets such as `make test`, `make lint`, `make api`, and `make docs`.
- `scripts/bijux-canon-ingest/openapi_drift.py` checks the checked-in schema against the FastAPI app.
- Root-managed repo config still lives outside the package, but package-owned paths and names now align with `bijux-canon-ingest`.

[Back to top](#project-tree--guide)
