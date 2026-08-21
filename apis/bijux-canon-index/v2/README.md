# Bijux Canon index artifact contract v2

This contract versions model locks, vectors, lexical and dense segments, filter
expressions, index generations, activation receipts, integrity records,
queries, candidates, fused hits, witnesses, approximation reports, executions,
provenance, and replay receipts. Each schema bundle exposes one closed
definition per artifact type and the manifest binds every public type to exact
schema bytes.

The canonical retrieval request binds query text to one corpus and immutable
index generation. It declares retrieval mode, per-channel candidate and
latency budgets, typed filters, deduplication and diversity policies, bounded
reranking, source/document/section scope, offline behavior, and the exact
trace content that must be retained. These fields are request inputs rather
than transport defaults, so CLI, HTTP, replay, and evaluation cannot silently
select different retrieval behavior.

Execution identity binds the normalized query-vector hash, immutable index
generation, backend and algorithm versions, index and query parameters,
filters, resource and recall budgets, software locks, hardware class,
candidate order, and result hash. Replay may therefore distinguish an output
change from input, implementation, hardware, or ordering drift.

Records use RFC 8785 canonical JSON. Their `artifact_id` is SHA-256 over the
complete canonical record after removing only the root `artifact_id`. Arrays
marked with `x-bijux-ordering` are sorted before identity calculation and are
never repaired on read.

Model locks bind immutable provider revisions, dimensions, dtypes,
normalization, pooling, tokenizer revisions, licenses, file hashes, and offline
policy. Generation records bind the complete admitted chunk set, its canonical
hash, lexical tokenizer, backend versions and parameter hashes, filters,
segments, build attempt, and parent generation/activation lineage. Generations
cannot activate until all referenced segments and vectors are durable and the
integrity record verifies. Activation receipts retain the previous generation
and atomic-write identity.

`sha256-merkle-v1` defines its manifest root as SHA-256 over the RFC 8785
canonical JSON bytes of the complete `members` array. Members are sorted by
`artifact_id`, are unique, and bind each referenced artifact to its canonical
content hash and byte length. This definition is intentionally domain-specific:
verifiers must not substitute a binary-tree Merkle construction.

Unknown schema versions, unregistered upgrades, and downgrades fail closed
according to [`migration-policy.json`](migration-policy.json).
