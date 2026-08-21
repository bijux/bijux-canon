# Bijux Canon index artifact contract v2

This contract versions model locks, vectors, lexical and dense segments, filter
expressions, index generations, activation receipts, and integrity records. The
single schema bundle exposes one closed definition per artifact type so the
manifest can bind every public type to the same immutable schema bytes.

Records use RFC 8785 canonical JSON. Their `artifact_id` is SHA-256 over the
complete canonical record after removing only the root `artifact_id`. Arrays
marked with `x-bijux-ordering` are sorted before identity calculation and are
never repaired on read.

Model locks bind immutable provider revisions, dimensions, dtypes,
normalization, pooling, tokenizer revisions, licenses, file hashes, and offline
policy. Generations cannot activate until all referenced segments and vectors
are durable and the integrity record verifies. Activation receipts retain the
previous generation and atomic-write identity.

`sha256-merkle-v1` defines its manifest root as SHA-256 over the RFC 8785
canonical JSON bytes of the complete `members` array. Members are sorted by
`artifact_id`, are unique, and bind each referenced artifact to its canonical
content hash and byte length. This definition is intentionally domain-specific:
verifiers must not substitute a binary-tree Merkle construction.

Unknown schema versions, unregistered upgrades, and downgrades fail closed
according to [`migration-policy.json`](migration-policy.json).
