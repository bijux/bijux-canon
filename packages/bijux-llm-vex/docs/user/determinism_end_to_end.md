# Deterministic Execution: End-to-End

## Why this exists

When systems behave differently in staging and production, teams lose weeks to debugging and lose trust in their results. Deterministic execution exists to prevent that drift by making “same input → same output” an enforceable guarantee.

If you skip determinism, you get subtle regressions: scores that change with no code changes, audits that can’t be replayed, and explanations that don’t hold up. This section is for anyone who needs to defend results in production—engineers, auditors, and operators.

## Story / scenario

You deploy a search change, and suddenly rankings differ between staging and prod. Users report inconsistent behavior, and the root cause is hidden randomness in the retrieval path.

## What usually goes wrong

- Approximate search sneaks into “exact” paths.
- Backends or embeddings change behavior without being captured in artifacts.
- Replay claims are made without a matching index or config.

## How Bijux-Vex handles it

Deterministic execution means **exact search, stable ordering, and replayable results**. If any component would violate determinism, the system refuses and explains why.

## What trade-offs remain

- Determinism can cost latency or scale.
- Some backends cannot provide exact guarantees.

## Where to go deeper

- `docs/user/deterministic_replay.md`
- `docs/user/determinism_refusals.md`

---

Requirements

- Execution contract: `deterministic`
- Exact-capable backend
- No ND-only features (ANN, approximate filters)

Supported backends

- Memory and SQLite adapters are deterministic exact.
- FAISS exact is deterministic if configured with exact index types.

What breaks determinism

- ANN indices or approximate search.
- Non-deterministic embeddings without explicit declarations.
- Backends that cannot guarantee exact search.

Replay semantics

- Replay is allowed only when fingerprints match.
- Replay is refused when index hash, config hash, or backend signature differs.

## Common misunderstandings

- “Exact means fast.” It can be slower than ANN, especially at scale.
- “Replay means same API payload.” Replay also requires matching artifacts and hashes.
- “Determinism is optional.” If you need audits, it is a requirement, not a preference.

## When to stop caring about determinism

If you only need approximate similarity for exploration, recommendations, or early-stage discovery, ND may be sufficient. Use deterministic execution when you need audits, regulatory defensibility, or rigorous regression checks. The key is to choose this consciously, not by accident.

CLI example

```bash
bijux vex ingest --doc "hello" --vector "[0.0, 1.0, 0.0]" \
  --vector-store memory

bijux vex materialize --execution-contract deterministic \
  --vector-store memory

bijux vex execute --artifact-id art-1 \
  --execution-contract deterministic --execution-intent exact_validation \
  --execution-mode strict --vector "[0.0, 1.0, 0.0]"
```

API example

```json
POST /execute
{
  "artifact_id": "art-1",
  "vector": [0.0, 1.0, 0.0],
  "top_k": 5,
  "execution_contract": "deterministic",
  "execution_intent": "exact_validation",
  "execution_mode": "strict"
}
```
