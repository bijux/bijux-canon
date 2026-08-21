# Bijux Canon ingest artifact contract v2

This directory owns immutable source, extracted document, corpus snapshot,
rejection, and lineage records for the ingest boundary. Each record is a closed
JSON Schema Draft 2020-12 object with a fixed `artifact_type` and
`schema_version`.

## Identity and serialization

Serialize records with RFC 8785 JSON Canonicalization Scheme. Reject duplicate
object keys and non-finite numbers. Unicode code points are preserved without
implicit normalization. To calculate `artifact_id`, remove only the root
`artifact_id` member, canonicalize the remaining complete record, hash those
bytes with SHA-256, and encode the result as `sha256:<lowercase hex>`.

Array order is semantic. Arrays marked with `x-bijux-ordering` must be sorted by
the declared key before identity calculation. Producers must never repair an
unsorted admitted record while reading it.

Payload fields point to immutable content-addressed objects. A record is not
admitted until its schema, identity, referenced payload digest, and referenced
artifact identities have all been verified.

## Migrations

[`migration-policy.json`](migration-policy.json) is the migration registry.
Version `2.0.0` has only a byte-identical identity transform. Unknown versions,
downgrades, and unregistered upgrades fail closed. A future transform must be
lossless, deterministic, adjacent-version, schema-validated on both sides, and
must produce a new artifact with explicit predecessor lineage.

## Schemas

- `source-record.schema.json` binds acquired bytes, origin, revision, and rights.
- `document-record.schema.json` binds an extracted document to its source.
- `corpus-snapshot-record.schema.json` freezes sorted admitted and rejected IDs.
- `rejection-record.schema.json` retains a stable reason and remediation.
- `lineage-record.schema.json` binds inputs and outputs to a reproducible operation.

The conformance bundle under `examples/` is derived from the repository's
25-document evaluation corpus and exercises every record type.
