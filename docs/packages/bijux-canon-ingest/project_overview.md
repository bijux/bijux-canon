# Project Tree & Guide

Quick map of the `bijux-canon-ingest` package directory.

## Package Layout

```text
.
├── docs/                          # package-local readme and contract anchors
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
├── mkdocs.yml                     # package docs site config
└── pyproject.toml                 # build metadata and dependencies
```

## Source Code

- `application/` keeps orchestration readable by splitting direct pipeline execution from pipeline definitions, indexing, querying, and service entrypoints.
- `application/index_runtime.py` holds the in-memory index runtime used by the public service facade so `application/service.py` stays a thin boundary instead of a grab bag of retrieval internals.
- `application/pipeline_definitions/compiler_support.py` is the explicit home for optional distributed compiler support state and typed errors.
- `interfaces/` holds adapter code that should not leak into the core model: CLI, HTTP, serialization, and error handling.
- `interfaces/cli/` now separates parser entrypoints from document IO helpers and command modules:
  `entrypoint.py`, `pipeline_commands.py`, `retrieval_commands.py`, `document_io.py`, and `document_pipeline.py`.
- `observability/` is a dedicated home for traces, taps, and deterministic execution summaries rather than hiding those concerns inside application code.
- `integrations/` and `safeguards/` make edge concerns explicit: optional third-party helpers on one side, operational protection on the other.
- `retrieval/` now separates dense retrieval, lexical retrieval, text analysis, and index builders instead of concentrating all of that logic in one file.
- `processing/`, `core/`, `retrieval/`, and `domain/` hold the main ingest and retrieval logic.

## Ideal Shape

- `core/`, `processing/`, and `retrieval/` own deterministic document cleaning, chunking, retrieval math, and index persistence.
- `domain/` owns protocols and effect descriptions, not concrete chunk embedding behavior or interface adapters.
- `infra/` owns concrete adapters such as clocks, storage implementations, and deterministic embedder adapters.
- `interfaces/` owns CLI, HTTP, serialization, and compatibility shims only.
- `application/` owns orchestration and boundary-focused service facades, not reusable retrieval internals that belong under `retrieval/`.

## What Does Not Belong Here

- App-specific workflow compilers that depend on Dask or Beam should stay outside the core ingest package until they are fully implemented and supported.
- CLI compatibility shims should not become the primary implementation home for document reading and chunk writing.
- Package-level `__init__` modules should not eagerly import CLI, HTTP, or indexing stacks just to expose a convenience symbol.

## Tests & Eval

- `tests/unit/` mirrors the runtime tree, including `application/`, `interfaces/`, `integrations/`, `safeguards/`, `retrieval/`, `domain/`, and other core support modules.
- `tests/e2e/` covers CLI and end-to-end retrieval flows.
- `tests/eval/` stores pinned corpus and query fixtures for evaluation gates.

## Config & Tooling

- `Makefile` drives package-local targets such as `make test`, `make lint`, `make api`, and `make docs`.
- `bijux_canon_dev.api.openapi_drift` checks the checked-in schema against the FastAPI app.
- Package-owned paths and names now align with the current ingest tree and its long-lived package boundaries.

[Back to top](#project-tree--guide)
