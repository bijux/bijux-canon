# Vector Store Semantics

## Why this exists

Vector stores look like databases, but they behave very differently. This section helps you avoid the most common operational mistakes—especially around deletion, consistency, and replay.

If you treat a vector store like a full database, you can end up with stale results, broken audits, or silent failures. This section is for anyone wiring storage into production systems.

## Story / scenario

A team deletes records in a vector store and assumes they are gone. Weeks later, the same vectors appear again after a restart because deletes were not persisted.

## What usually goes wrong

- Deletes are treated like database deletes.
- ANN indices are assumed to update automatically.
- Consistency is assumed without checking.

## How Bijux-Vex handles it

Vector stores are adapters with explicit capabilities. Bijux-Vex does not assume database semantics.

## What trade-offs remain

- Some backends require rebuilds for safe deletes.
- Remote stores may be eventual rather than read-after-write.

## Where to go deeper

- `docs/user/vectorstores/faiss.md`
- `docs/user/vectorstores/qdrant.md`

---

Exact vs ANN

- Exact search is deterministic and replayable.
- ANN is ND and must declare randomness and bounds.

Delete semantics

- Deletes must be persisted or explicitly refused.
- If a backend cannot guarantee delete semantics, the operation fails.

Rebuild and compaction

- Some backends require rebuild after deletes.
- Compaction is explicit and never implicit.

Consistency guarantees

- Local stores are typically read-after-write consistent.
- Remote stores may be eventual; this is recorded in capabilities and provenance.

Backend differences

- FAISS: local, fast, exact and ANN depending on index type.
- Qdrant: remote, supports filters and ANN, may be eventual.
- Memory/SQLite: deterministic exact only.

## Common misunderstandings

- “Deletes are always permanent.” They are not unless the backend guarantees it.
- “ANN and exact are interchangeable.” They are not.
- “Consistency is implicit.” It must be checked and declared.
