
# Changelog

## v0.1.0 — Initial public release

- Evidence & citations: byte-span + sha256 verification, fail-closed grounding, replayable traces.
- Retrieval: chunked BM25 with pinned corpus/index provenance, deterministic rankings, replay guards.
- Reasoning: structured claims with enforced supports, insufficiency handling, baseline deterministic reasoner.
- Verification: strict invariant checks, negative-capability tests, invariant IDs wired to failures.
- API: SQLite-backed lifecycle, stateful Schemathesis coverage, auth + rate limiting + quotas.
- Tooling: make lint/test/quality/security/api gates, docs site, frozen contract scope `release_scope_v0_1_0.md`.
