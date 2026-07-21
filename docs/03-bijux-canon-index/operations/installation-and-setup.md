---
title: Installation and Setup
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Installation and Setup

`bijux-canon-index` supports Python 3.11 through 3.14. Install the base package
for the typed execution engine, module CLI, FastAPI application, and local
memory or SQLite paths. Add extras only for the adapters an environment uses.

```mermaid
flowchart LR
    P[Install base package] --> C[Discover capabilities]
    C --> S[Choose optional adapters]
    S --> W[Initialize governed state]
    W --> D[Validate a dry-run plan]
    D --> R[Retain backend and artifact identity]
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install bijux-canon-index
```

The canonical wheel does not currently register a `bijux-canon-index`
executable. Verify the import and invoke the Typer application as a module:

```bash
python -c "import bijux_canon_index; print(bijux_canon_index.__version__)"
python -m bijux_canon_index.interfaces.cli.app --help
python -m bijux_canon_index.interfaces.cli.app capabilities
```

## Choose Optional Capabilities

```bash
# YAML configuration files
python -m pip install 'bijux-canon-index[config]'

# hnswlib approximate-nearest-neighbor execution
python -m pip install 'bijux-canon-index[nd]'

# NumPy, FAISS, and Qdrant client adapters
python -m pip install 'bijux-canon-index[vdb]'

# Uvicorn and API validation dependencies
python -m pip install 'bijux-canon-index[api]'
```

Extras install client libraries, not external services. A Qdrant deployment
still needs an accessible service and its own authentication, persistence, and
backup configuration. Capability discovery reports whether an adapter can
actually be used in the current environment.

## Initialize Local State

```bash
mkdir -p artifacts/bijux-canon-index
python -m bijux_canon_index.interfaces.cli.app init \
  --config-path artifacts/bijux-canon-index/config.toml
python -m bijux_canon_index.interfaces.cli.app doctor
```

By default, SQLite state, embedding cache, and run records stay under
`artifacts/bijux-canon-index/`. For a service or scheduled job, pin the run
directory rather than relying on its working directory:

```bash
export BIJUX_CANON_INDEX_RUN_DIR=/var/lib/bijux-canon-index/runs
```

The selected operating-system user must be able to create and atomically
replace files in that directory.

## Run a Smoke Execution

```bash
python -m bijux_canon_index.interfaces.cli.app execute \
  --vector '[0.2, 0.8]' \
  --artifact-id setup-smoke \
  --execution-contract deterministic \
  --execution-intent exact_validation \
  --execution-mode strict \
  --top-k 1 \
  --dry-run

python -m bijux_canon_index.interfaces.cli.app list-runs --limit 5
```

The dry run validates planning without claiming that retrieval occurred. Use a
real artifact and omit `--dry-run` only after the chosen backend and corpus are
configured.

## Serve the HTTP Boundary

With the `api` extra installed:

```bash
uvicorn bijux_canon_index.api.v1.app:app \
  --host 127.0.0.1 \
  --port 8000
```

Then inspect capabilities:

```bash
curl --fail-with-body http://127.0.0.1:8000/capabilities
```

## Repository Checkout

```bash
make install
make -f makes/packages/bijux-canon-index.mk \
  -C packages/bijux-canon-index help
make test PACKAGE=bijux-canon-index
```

Package Makefiles are repository profiles under `makes/packages/`; the package
directory does not contain a standalone Makefile. Use the root dispatcher for
normal checks and the explicit profile form when inspecting package targets.

Use `make docs-check` for handbook changes. Repository-wide validation is
reserved for changes that cross package, API, build, or release boundaries.

## Setup Checklist

- The canonical import and module CLI resolve from the same environment.
- Capability output matches the intended deterministic or ANN execution mode.
- Optional native libraries and external services are installed separately and
  report healthy.
- State, cache, and run paths are explicit and writable.
- The application understands which backend state must accompany run evidence
  for replay.

Continue with [state and persistence](../architecture/state-and-persistence.md)
and [entrypoint examples](../interfaces/entrypoints-and-examples.md).
