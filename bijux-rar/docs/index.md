STATUS: EXPLANATORY  
# bijux-rar

[![PyPI](https://img.shields.io/pypi/v/bijux-rar.svg)](https://pypi.org/project/bijux-rar/)
[![Python](https://img.shields.io/pypi/pyversions/bijux-rar.svg)](https://pypi.org/project/bijux-rar/)
[![License](https://img.shields.io/github/license/bijux/bijux-rar.svg?logo=open-source-initiative&logoColor=white)](https://github.com/bijux/bijux-rar/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://bijux.github.io/bijux-rar/)
[![CI](https://github.com/bijux/bijux-rar/actions/workflows/ci.yml/badge.svg)](https://github.com/bijux/bijux-rar/actions/workflows/ci.yml)

**bijux-rar** is a deterministic retrieval-augmented reasoning (RAR) engine.

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

bijux-rar enforces:
- deterministic execution,
- immutable artifacts,
- cryptographically stable traces,
- replay and verification by default.

If a run cannot be replayed and verified byte-for-byte, it is considered invalid.

---

## Installation

```bash
pip install bijux-rar
````

Python ≥ 3.10 is required.

---

## Minimal usage

### CLI

```bash
bijux-rar run \
  --spec examples/spec.json \
  --artifacts-dir artifacts/runs \
  --seed 0

RUN_DIR=$(cat artifacts/runs/latest.txt 2>/dev/null || ls artifacts/runs | head -n1)

bijux-rar verify \
  --trace artifacts/runs/$RUN_DIR/trace.jsonl \
  --plan artifacts/runs/$RUN_DIR/plan.json \
  --fail-on-verify

bijux-rar replay \
  --trace artifacts/runs/$RUN_DIR/trace.jsonl \
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

bijux-rar is intentionally narrow in scope.

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
  [https://github.com/bijux/bijux-rag](https://github.com/bijux/bijux-rag)

bijux-rar sits beneath both, enforcing execution and verification invariants.

---

## Documentation

Authoritative documentation is published at:

[https://bijux.github.io/bijux-rar/](https://bijux.github.io/bijux-rar/)

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

MIT. See `LICENSE`.
