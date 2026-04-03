# Project Tree & Guide

Quick map of the `bijux-canon-ingest` package directory.

## Package Layout

```text
.
├── docs/                          # package docs, ADRs, and references
├── src/bijux_canon_ingest/        # library code
│   ├── application/               # orchestration and workflow assembly
│   ├── config/                    # configuration models and dependency builders
│   ├── core/                      # core types, rules, and dedup helpers
│   ├── domain/                    # effect descriptions and domain capabilities
│   ├── fp/                        # functional helper internals
│   ├── infra/                     # runtime adapters
│   ├── integrations/              # optional ecosystem integrations
│   ├── interfaces/                # cli, http, serialization, and error adapters
│   ├── observability/             # traces, taps, and execution summaries
│   ├── processing/                # pure ingest transforms
│   ├── result/                    # result and option helpers
│   ├── retrieval/                 # indexing, retrieval, reranking, and answering
│   ├── safeguards/                # retries, breakers, reports, and resource guards
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

- `application/` keeps orchestration readable by splitting direct pipeline execution from pipeline definitions, indexing, querying, and service entrypoints.
- `interfaces/` holds adapter code that should not leak into the core model: CLI, HTTP, serialization, and error handling.
- `observability/` is a dedicated home for traces, taps, and deterministic execution summaries rather than hiding those concerns inside application code.
- `integrations/` and `safeguards/` make edge concerns explicit: optional third-party helpers on one side, operational protection on the other.
- `processing/`, `core/`, `retrieval/`, and `domain/` hold the main ingest and retrieval logic.

## Tests & Eval

- `tests/unit/` mirrors the runtime tree, including `application/`, `interfaces/`, `integrations/`, `safeguards/`, `retrieval/`, `domain/`, and other core support modules.
- `tests/e2e/` covers CLI and end-to-end retrieval flows.
- `tests/eval/` stores pinned corpus and query fixtures for evaluation gates.

## Config & Tooling

- `Makefile` drives package-local targets such as `make test`, `make lint`, `make api`, and `make docs`.
- `scripts/bijux-canon-ingest/openapi_drift.py` checks the checked-in schema against the FastAPI app.
- Package-owned paths and names now align with the current ingest tree and its long-lived package boundaries.

[Back to top](#project-tree--guide)
