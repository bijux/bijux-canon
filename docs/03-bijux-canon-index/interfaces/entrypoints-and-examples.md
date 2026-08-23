---
title: Entrypoints and Examples
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Entrypoints and Examples

The package provides Python, installed CLI, module CLI, and HTTP surfaces. The
wheel registers `bijux-canon-index`; the module form invokes the same public
application.

## Inspect capabilities before execution

Capabilities are the first useful call because they reveal the selected
backend and the contracts it can satisfy.

```bash
bijux-canon-index capabilities
```

The same discovery path is available in process:

```python
from bijux_canon_index.application.engine import VectorExecutionEngine

engine = VectorExecutionEngine()
capabilities = engine.capabilities()
print(capabilities["execution"])
```

The package root currently exposes version metadata only. Import application,
domain, or core types from their owning modules rather than relying on
undocumented root re-exports.

## Execute a deterministic request

An execution must state why the result is needed, the required contract, and
the refusal posture:

```bash
python -m bijux_canon_index.interfaces.cli.app execute \
  --vector '[0.2, 0.8]' \
  --artifact-id corpus-retention \
  --execution-contract deterministic \
  --execution-intent exact_validation \
  --execution-mode strict \
  --top-k 5
```

Use `--dry-run` to validate and render the plan without executing it. Add
`--explain` when the response should include the execution explanation. Budget
options such as `--max-latency-ms`, `--max-memory-mb`, and `--max-error` become
part of the request rather than informal operator expectations.

## Declare an approximate request honestly

Non-deterministic execution requires explicit randomness and ANN policy. A
seeded, bounded example is:

```bash
python -m bijux_canon_index.interfaces.cli.app execute \
  --vector '[0.2, 0.8]' \
  --artifact-id corpus-retention \
  --execution-contract non_deterministic \
  --execution-intent exploratory_search \
  --execution-mode bounded \
  --randomness-seed 42 \
  --randomness-sources ann \
  --randomness-bounded \
  --nd-profile balanced \
  --nd-target-recall 0.95 \
  --nd-witness-mode sample \
  --nd-witness-sample-k 20
```

If a run has no reproducible seed, declare `--randomness-non-replayable` rather
than implying that captured output is replayable.

## Write machine-readable output

Global CLI options precede the command:

```bash
python -m bijux_canon_index.interfaces.cli.app \
  --format json \
  --output artifacts/bijux-canon-index/capabilities.json \
  capabilities
```

`init` creates a local configuration and the package artifact directories.
`list-runs`, `list-artifacts`, `audit`, `validate`, and `doctor` expose the
operational state without requiring callers to inspect internal storage.

## Serve the HTTP API

The supported FastAPI application is exported from `api.v1`:

```bash
uvicorn bijux_canon_index.api.v1.app:app --host 127.0.0.1 --port 8000
```

Capability discovery requires no request body:

```bash
curl --fail-with-body http://127.0.0.1:8000/capabilities
```

The v1 surface includes:

| Purpose | Operation |
| --- | --- |
| discover backend and inventory | `GET /capabilities`, `GET /artifacts`, `GET /runs` |
| create and populate a corpus | `POST /create`, `POST /ingest` |
| materialize an execution artifact | `POST /artifact` |
| execute and interpret retrieval | `POST /execute`, `POST /explain`, `POST /replay` |

Request fields and response envelopes are pinned in the
[`v1 OpenAPI schema`](https://github.com/bijux/bijux-canon/blob/main/apis/bijux-canon-index/v1/schema.yaml).
Use the schema rather than translating CLI option names into HTTP fields by
guesswork.
