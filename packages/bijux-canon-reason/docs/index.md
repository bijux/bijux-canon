STATUS: EXPLANATORY  
# bijux-canon-reason

[![PyPI](https://img.shields.io/pypi/v/bijux-canon-reason.svg)](https://pypi.org/project/bijux-canon-reason/)
[![Python](https://img.shields.io/pypi/pyversions/bijux-canon-reason.svg)](https://pypi.org/project/bijux-canon-reason/)
[![License](https://img.shields.io/github/license/bijux/bijux-canon.svg?logo=open-source-initiative&logoColor=white)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://bijux.github.io/bijux-canon-reason/)

**bijux-canon-reason** is a deterministic retrieval-augmented reasoning (RAR) engine.

The legacy package name `bijux-rar` remains available as a compatibility shim that installs `bijux-canon-reason`.

It produces **byte-stable traces**, **versioned artifacts**, and **verifiable provenance**
for every run. Execution, verification, and replay are first-class constraints,
not optional features.

---

## Why this exists

Most RAG / RAR systems are:
- non-deterministic,
- impossible to replay,
- unverifiable after the fact,
- dependent on trust in the author or runtime.

bijux-canon-reason enforces:
- deterministic execution,
- immutable artifacts,
- cryptographically stable traces,
- replay and verification by default.

If a run cannot be replayed and verified byte-for-byte, it is considered invalid.

---

## Installation

```bash
pip install bijux-canon-reason
```

Legacy alias:

```bash
pip install bijux-rar
```

Python ≥ 3.11 is required.

---

## Minimal usage

### CLI

```bash
bijux-canon-reason run \
  --spec examples/spec.json \
  --artifacts-dir artifacts/bijux-canon-reason \
  --seed 0

RUN_DIR=$(cat artifacts/bijux-canon-reason/runs/latest.txt 2>/dev/null || ls artifacts/bijux-canon-reason/runs | head -n1)

bijux-canon-reason verify \
  --trace artifacts/bijux-canon-reason/runs/$RUN_DIR/trace.jsonl \
  --plan artifacts/bijux-canon-reason/runs/$RUN_DIR/plan.json \
  --fail-on-verify

bijux-canon-reason replay \
  --trace artifacts/bijux-canon-reason/runs/$RUN_DIR/trace.jsonl \
  --fail-on-diff
```

Verification or replay failures indicate invariant violations.

---

### HTTP API

```bash
uvicorn bijux_rar.httpapi:app --host 127.0.0.1 --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d @examples/spec.json
```

The API exposes the same deterministic contracts as the CLI.

---

## Project boundaries

bijux-canon-reason is intentionally narrow in scope.

It is **not**:

* a chat framework,
* a prompt playground,
* a generic RAG toolkit,
* an experimentation sandbox.

It is a **core execution and verification engine**.

---

## Relationship to other bijux projects

* **bijux-cli** — shared CLI conventions and scaffolding
  [https://github.com/bijux/bijux-cli](https://github.com/bijux/bijux-cli)

* **bijux-rag** — retrieval layer and corpus tooling
  [https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest](https://github.com/bijux/bijux-canon/tree/main/packages/bijux-canon-ingest)

bijux-canon-reason sits beneath both, enforcing execution and verification invariants.

---

## Documentation

Authoritative documentation is published at:

[https://bijux.github.io/bijux-canon-reason/](https://bijux.github.io/bijux-canon-reason/)

The documentation is part of the system contract.
Code and docs are tested for drift.

---

## Stability and compatibility

**Initial public release: v0.1.0**

* Core contracts are frozen.
* Breaking changes require explicit versioning and migration.
* Determinism and replay invariants will not be relaxed.

---

## License

Apache License 2.0. See [LICENSE](https://github.com/bijux/bijux-canon/blob/main/LICENSE).
