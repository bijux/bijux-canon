---
title: Installation and Setup
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Installation and Setup

`bijux-canon-ingest` supports Python 3.11 through 3.14. The base installation
includes typed document processing, MessagePack serialization, NumPy retrieval,
the CLI, and the FastAPI boundary.

## Install the Canonical Package

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install bijux-canon-ingest
```

Confirm both the import and command entry point:

```bash
python -c "import bijux_canon_ingest; print(bijux_canon_ingest.__version__)"
bijux-canon-ingest --help
```

New applications should install the canonical distribution. Install
`bijux-rag` only when an existing application still requires the legacy
`bijux_rag` import or `bijux-rag` command.

## Prepare a First Input

The command workflow accepts CSV documents. A minimal file has the fields
needed by `RawDoc`:

```csv
doc_id,title,abstract,categories
policy-17,Retention policy,Keep signed run records for seven years.,governance
policy-23,Access policy,Review privileged access every quarter.,security
```

Save it as `documents.csv`, then inspect the installed command's options before
choosing a pipeline configuration:

```bash
bijux-canon-ingest --help
bijux-canon-ingest index build --help
```

Keep local output outside the source tree:

```bash
mkdir -p artifacts/ingest
bijux-canon-ingest index build \
  --input documents.csv \
  --out artifacts/ingest/policies.index \
  --backend bm25

bijux-canon-ingest retrieve \
  --index artifacts/ingest/policies.index \
  --query "privileged access" \
  --top-k 3
```

BM25 requires no model download. The `numpy-cosine` backend can use the
deterministic `hash16` embedding for local and test workflows; external model
adapters may introduce their own model files, credentials, network access, and
resource requirements.

## Use the Library Directly

```python
from bijux_canon_ingest import RagEnv, RawDoc, chunk_doc, clean_doc

doc = RawDoc(
    doc_id="policy-17",
    title="Retention policy",
    abstract="Keep signed run records for seven years.",
    categories="governance",
)

chunks = chunk_doc(clean_doc(doc), RagEnv(chunk_size=80, overlap=10))
print(chunks[0])
```

The root import is the stable home for dependency-light primitives. Import
application, interface, storage, or adapter modules only when the integration
needs that boundary.

## Repository Checkout

For contribution work from the monorepo root:

```bash
make install
make -C packages/bijux-canon-ingest help
make -C packages/bijux-canon-ingest test
```

Use the package tests for the first feedback loop and `make docs-check` for
public documentation. Repository-wide `make check` and `make test-all` are
broader release or integration lanes, not required for routine documentation
work.

## Setup Checklist

- Python is within the supported range and the intended virtual environment is
  active.
- `bijux_canon_ingest` imports and reports a version.
- `bijux-canon-ingest --help` resolves from the same environment.
- Input identifiers are stable and output paths are caller-owned.
- The selected embedding backend's model and credential requirements are known.
- A saved index can be loaded and queried before it becomes a downstream
  dependency.

For serialization and path behavior, continue with
[state and persistence](../architecture/state-and-persistence.md). For command
failures and exit behavior, see [failure recovery](failure-recovery.md).
