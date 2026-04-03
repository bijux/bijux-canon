STATUS: EXPLANATORY

# Tests

Tests are **mandatory**, required, and enforced; benchmarks accompany critical paths.

All changes must pass the full test suite via `make all`.  
There is no partial, advisory, or best-effort testing mode.

---

## Scope

The test suite covers the following guarantees:

- **Determinism**
  - Planner output stability
  - Executor ordering and topology enforcement
  - Cross-platform fingerprint stability

- **Core invariants**
  - Trace structure and ordering
  - Artifact and manifest integrity
  - ID and hash stability

- **Verification**
  - Evidence span and hash validation
  - Provenance enforcement
  - Verification failure modes

- **Serialization**
  - Canonical JSON encoding
  - JSONL round-trip stability
  - Trace and artifact compatibility checks

- **Runtime behavior**
  - Frozen runtime determinism
  - Tool invocation ordering
  - Replay safety and diff detection

- **End-to-end gates**
  - CLI smoke tests
  - Deterministic replay (fingerprint + diff)
  - HTTP API smoke and contract tests

---

## Enforcement

- Tests are executed automatically by CI
- Coverage is enforced for `src/bijux_rar`
- Determinism and replay gates are non-optional

A test failure indicates a contract violation.

---

## Running locally

```bash
make test
````

Runs the full pytest suite, including coverage and invariant checks.

```bash
make replay_gate
```

Runs determinism-only replay and diff enforcement.

---

## Contribution policy

Pull requests that:

* reduce coverage,
* weaken determinism,
* relax invariants,
* or bypass replay checks

will be rejected.
