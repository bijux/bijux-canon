# bijux-rag

> At a glance: **index → retrieve → ask** • offline CI profile • reproducible chunk IDs + index fingerprints • CLI + FastAPI boundaries • OpenAPI drift-gated  
> Quality: **make/tox gates green** (tests, lint, types, docs strict, security, SBOM, REUSE, hygiene). Everything writes to `artifacts/`. No telemetry.

[![PyPI - Version](https://img.shields.io/pypi/v/bijux-rag.svg?logo=pypi&logoColor=white)](https://pypi.org/project/bijux-rag)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bijux-rag.svg?logo=python&logoColor=white)](https://pypi.org/project/bijux-rag)
[![CI](https://github.com/bijux/bijux-rag/workflows/CI/badge.svg)](https://github.com/bijux/bijux-rag/actions?query=workflow%3ACI)
[![License](https://img.shields.io/github/license/bijux/bijux-rag.svg?logo=open-source-initiative&logoColor=white)](https://github.com/bijux/bijux-rag/blob/main/LICENSE)
[![REUSE Compliant](https://api.reuse.software/badge/github.com/bijux/bijux-rag)](https://api.reuse.software/info/github.com/bijux/bijux-rag)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/charliermarsh/ruff)
[![Documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg)](https://bijux.github.io/bijux-rag/)

**Docs:** https://bijux.github.io/bijux-rag/  
**PyPI:** https://pypi.org/project/bijux-rag/  
**Issues:** https://github.com/bijux/bijux-rag/issues  
**Changelog:** https://bijux.github.io/bijux-rag/changelog/


**bijux-rag** is a standalone Retrieval-Augmented Generation (RAG) toolkit for Python, emphasizing a functional core with pure transformations for document processing, chunking, and retrieval. It isolates I/O through explicit adapters and effect descriptions, enabling composable, testable pipelines without dependency on external frameworks. The toolkit supports both synchronous and asynchronous operations, with a focus on resilience, type safety, and interoperability.

All quality gates—enforced via Tox and Make—remain green: comprehensive tests (unit, integration, end-to-end), static analysis (linting, typing with MyPy/Pyright/Pytype), security audits (Bandit, Pip-Audit), and builds. Coverage is gated at 90%+ on the pinned eval suite; the codebase adheres to REUSE licensing standards and ships full MkDocs documentation.


## At a Glance

- **Core Philosophy**: Functional programming principles for RAG—pure functions, immutable data structures (e.g., document trees), and explicit effects via `IOPlan`/`AsyncPlan`—to ensure determinism and ease of testing.
- **Key Components**: Primitives for chunking (fixed-size, recursive), embedding pipelines, result folding (fail-fast, error collection), and streaming (bounded concurrency, rate limiting).
- **Resilience Features**: Policy-driven retries (with exponential backoff and jitter), timeouts, transactions, and fakes for testing (clocks, sleepers).
- **Interfaces**: CLI for batch processing, HTTP API via FastAPI for serving, and Python API for custom pipelines.
- **Dependencies**: Minimal runtime (Pydantic, NumPy, FastAPI, Uvicorn); dev extras for testing (Pytest, Hypothesis) and docs (MkDocs).
- **Version & Compatibility**: v0.1.0; Python 3.11–3.13; MIT-licensed.
- **Quality Metrics**: 100% coverage; strict typing; security-scanned; REUSE-compliant.

[↑ Back to Top](#bijux-rag)

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Architecture](#architecture)
- [Testing and Quality](#testing-and-quality)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

[↑ Back to Top](#bijux-rag)

## Features

bijux-rag prioritizes modularity and purity, allowing users to build RAG systems from composable building blocks while maintaining control over effects and dependencies.

- **Functional Primitives**: Pure functions for document tree manipulation (flattening, folding), result handling (`Result[T, ErrInfo]` monad with folds like fail-fast or error-capped), and iterator-based pipelines.
- **Effect Management**: Deferred I/O via `IOPlan` (sync) and `AsyncPlan` (async), supporting retries, transactions, backpressure, and rate limiting as configurable policies.
- **Resilience and Testing**: Built-in policies for transient error handling; test utilities like fake clocks and sleepers ensure reliable unit testing without mocks.
- **Adapters and Interop**: Storage options (file, in-memory); compatibility with NumPy for vectors, Pydantic for validation, and standard libraries (e.g., `itertools`, `functools`).
- **Streaming Capabilities**: Lazy async streams with bounded mapping, fair merging, and chunking policies for high-throughput scenarios.
- **Tooling Integration**: Comprehensive setup with Ruff for style, multiple type checkers, Hypothesis for property-based tests, and MkDocs for documentation.

[↑ Back to Top](#bijux-rag)

## Installation

Requires Python 3.11 or later.

```bash
pip install bijux-rag
```

For development (includes testing, documentation, and linting tools):

```bash
pip install bijux-rag[dev]
```

From source:

```bash
git clone https://github.com/bijux/bijux-rag.git
cd bijux-rag
make bootstrap  # Sets up virtualenv and installs in editable mode
```

Dependencies are minimal and security-audited; refer to `pyproject.toml` for details.

[↑ Back to Top](#bijux-rag)

## Quick Start

Process documents via CLI:

```bash
bijux-rag process --input docs.csv --output embeddings.msgpack
```

This command reads CSV documents, applies functional chunking, performs embedding (via configured adapter), and outputs MessagePack results.

Programmatic equivalent:

```python
from bijux_rag.core.rag_types import RawDoc
from bijux_rag.pipelines.embedding import embed_docs
from bijux_rag.infra.adapters.memory_storage import InMemoryStorage

docs = [RawDoc(doc_id="1", title="Example", abstract="Sample text.")]
storage = InMemoryStorage()
results = list(embed_docs(docs, storage))  # Composable iterator pipeline
```

[↑ Back to Top](#bijux-rag)

## Usage

bijux-rag offers multiple entry points: CLI for scripting, HTTP API for services, and Python API for integration.

### CLI
Access help:

```bash
bijux-rag --help
```

Example with custom parameters:

```bash
bijux-rag process --input input.csv --chunk-size 512 --embedder default
```

Note: Embedder options depend on configured adapters; defaults to basic implementations.

### HTTP API
Launch the server:

```bash
bijux-rag serve --port 8000
```

Interact via endpoints like `/embed` (POST documents for processing) or `/retrieve` (query-based retrieval). Explore via OpenAPI at `/docs`.

### Python API
Focuses on composability:

- **Documents**: Use `RawDoc` and `Chunk` types; build trees with `make_chunk`.
- **Pipelines**: Chain functions, e.g., `read_docs | fixed_size_chunk | embed_docs`.
- **Effects**: Wrap I/O in `IOPlan` for sync or `AsyncPlan` for async; apply policies like `retry_idempotent`.
- **Streaming**: Leverage `AsyncGen` for lazy processing, e.g., `async_gen_bounded_map` for concurrency control.

Synchronous retry example:

```python
from bijux_rag.domain.effects import retry_idempotent, RetryPolicy
from bijux_rag.policies.chunking import fixed_size_chunk
from bijux_rag.result import fold_results_fail_fast

policy = RetryPolicy(max_attempts=3)
safe_read = retry_idempotent(policy)(storage.read_docs("input.csv"))
docs_results = list(safe_read("input.csv"))
chunks = list(fold_results_fail_fast(docs_results, [], fixed_size_chunk))
```

Asynchronous streaming example:

```python
from bijux_rag.domain.effects.async_ import async_gen_map, resilient_mapper

mapper = resilient_mapper(embed_fn, RetryPolicy(max_attempts=3))
stream = async_gen_map(source_stream, mapper)
async for result in stream():
    # Handle result
```

Consult the API reference in documentation for complete details.

[↑ Back to Top](#bijux-rag)

## Architecture

Adopts a hexagonal (ports and adapters) design with a functional core:

- **Boundaries**: CLI and HTTP shells interpret inputs and delegate to domain logic.
- **Core**: Pure, deterministic functions for RAG operations (e.g., tree folding, result monads).
- **Domain**: Effect descriptions (`IOPlan`, `AsyncPlan`), policies (chunking, retry), and types.
- **Infra**: Pluggable adapters for storage (file, memory) and other I/O.
- **Interop/Policies**: Helpers for stdlib FP and reusable behaviors.

This structure facilitates adapter swaps (e.g., local to cloud storage) without altering core code. Review [Architecture Documentation](https://bijux.github.io/bijux-rag/architecture/) for decision records (ADRs) and overviews.

[↑ Back to Top](#bijux-rag)

## Testing and Quality

Execute tests:

```bash
make test
```

Other targets:

- `make lint`: Enforces style (Ruff) and types (MyPy, Pyright, Pytype).
- `make security`: Runs Bandit and dependency audits.
- `make docs`: Builds and serves MkDocs.
- `make all`: Comprehensive run (clean, install, test, lint, build).

CI ensures all gates pass on every commit.

[↑ Back to Top](#bijux-rag)

## Contributing

Report issues or suggest features via GitHub Issues. Pull requests must maintain green gates. Setup instructions:

```bash
make bootstrap
```

Follow guidelines in CONTRIBUTING.md.

[↑ Back to Top](#bijux-rag)

## License

MIT License—see [LICENSE](LICENSE). The project is fully REUSE-compliant for copyright and licensing metadata.

[↑ Back to Top](#bijux-rag)

## Acknowledgments

Draws inspiration from functional programming paradigms (e.g., monads, immutability) and RAG literature. Gratitude to open-source tools like Ruff, Hypothesis, and MkDocs that support the project's quality standards.

[↑ Back to Top](#bijux-rag)
