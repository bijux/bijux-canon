---
title: Data Contracts
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-08-23
---

# Data Contracts

Ingest has five distinct contract layers: canonical source metadata, canonical
corpus snapshots, functional source records, in-process chunk values, and
serialized boundary models. They are related, but they are not interchangeable.

## Canonical Source Metadata

`normalize_source_metadata()` resolves bibliographic metadata by declared
source type, never by mapping merge order or caller iteration order. For
bibliographic fields the fixed precedence is:

```text
user override
  > corpus lock
  > acquisition receipt
  > embedded/parser metadata
  > filename fallback
```

Records at the same level are ordered by their provenance label and exact
record hash, so changing input iteration order cannot change the result.

Discovery remains authoritative for the admitted relative path, media type,
content SHA-256, and byte length. A filename stem is used as a title only when
no higher source supplied a title; reviewed metadata is therefore never
replaced by a filename guess.

The `bijux.canon.ingest.source_metadata.v2` manifest retains every contributing
record's source type, label, exact record hash, optional source-content hash,
and contributed fields. Each raw field also retains its original and normalized
value. `selected_values` identifies the winning contribution for each field,
while `conflicts` records every normalized disagreement with that selection.
Equivalent Unicode, URI, DOI, date, language, license, and author forms do not
create false conflicts.

Identity evidence fails closed. A declared record identity must match its
canonical record, and any supplied source format, hash, or byte length must
match the admitted immutable source. A DOI and DOI-based canonical URI that
identify different works are rejected with `MetadataIntegrityError`; ordinary
metadata disagreement remains visible as a conflict rather than being
overwritten.

Every supported parser contributes one `embedded_parser` record bound to its
parser manifest, source hash, format, and byte length. JATS and HTML contribute
their structured citation fields; PDF and DOCX contribute embedded properties
and semantic titles; Markdown contributes bounded top-level front-matter
fields; and plain text contributes an identified title block when present.
These records use the same resolver as reviewed records, so an unlocked corpus
selects real parser truth while a lock can override it without erasing the
parser value or disagreement.

### Corpus Lock Resolution

Canonical directory ingest checks for `corpus.lock.json` in the document root,
its parent, and—when ingesting a conventional `corpus/sources` directory—the
portfolio root. `corpus_lock_path` (Python and HTTP) or `--corpus-lock` (CLI)
selects an explicit lock. When no lock is present, ingest remains available and
the metadata manifest retains lower-provenance discovery and parser records,
using the filename only when no parser or supplied record exposes a title.

The loader accepts the governed parser-source and research-corpus lock schemas.
Before parsing, it verifies the canonical lock identity, aggregate and per-file
counts and sizes, portable paths, exact source hashes, compatible media types,
license expression and URL, and linked source/acquisition identities. The
parser portfolio also verifies its source JSON, acquisition receipts, transport
checksums, and license-evidence checksums. The research portfolio verifies its
materialization manifest, exact manifest hash, portfolio identity, and linked
acquisition identities. A stale, partial, extra, malformed, ambiguous, escaped,
or tampered chain fails with `CorpusLockError` and a stable issue code.
Preparation manifests use `bijux.canon.ingest.corpus_preparation.v2` and retain
the portable lock schema, identity, source count, and automatic-or-explicit
discovery mode. Snapshot assembly continues to accept identity-valid v1
preparations as unlocked legacy inputs. Ingest result manifests expose the same
portable lock summary, or `{"status": "absent"}`; neither persisted form
leaks the host path of the selected lock.

## Canonical Corpus Snapshot

Every admitted snapshot document carries an ingest-owned
`bijux.canon.ingest.document_citation_lineage.v1` graph. It binds the immutable
source SHA-256, document identity, parser name/version and parser-manifest
identity to every normalized mapping and semantic chunk. Each
source-to-document, document-to-mapping, and mapping-to-chunk edge has its own
content identity.

A chunk can combine several semantic blocks. Its lineage therefore contains an
ordered locator segment for every contributing mapping rather than inventing
one locator for the combined text. Segment spans use Unicode code-point
coordinates in the normalized chunk and retain the actual format locator:
JATS element path, PDF page text span, HTML DOM path, Markdown or text line
span, or OOXML package-part/block coordinates. Exact segment text remains in
the sibling chunk record and is bound by SHA-256; repeated text is resolved by
the structural locator, never by searching for the quotation.

Resolution verifies the whole source payload identity, parser manifest,
document and mapping identities, normalized offsets, exact text hash, and the
format locator. Missing and multiply resolving locators are typed
`locator_unavailable` and `locator_ambiguous` refusals. PDF and OOXML locators
identify text in a deterministic parser representation bound to the exact
source payload; they do not pretend compressed container bytes are direct text
coordinates.

## Immutable Snapshot Publication

`bijux.canon.ingest.corpus_publication.v2` is the active-generation manifest.
It binds the canonical snapshot bytes and snapshot identity to a
`bijux.canon.ingest.corpus_object_relation.v1` identity, plus explicit source
and derived relation-entry counts. The relation enumerates the exact source
bytes, canonical snapshot, parsed-document and metadata manifests,
citation-lineage graph, normalized mappings, and semantic chunks. Every entry
records its kind, document identity, stable domain identity, byte length, and
SHA-256 content address.

Object counts describe logical relation entries; identical byte payloads may
share one physical content-addressed object. A reader accepts the publication
only after canonical JSON, snapshot identity, relation identity, entry counts,
every reachable object digest, and the snapshot-object binding all verify.
Version 1 generation manifests remain readable for existing stores but do not
claim the version 2 relation guarantees.

## Source Record

`RawDoc` represents one source row:

| Field | Type | Meaning |
| --- | --- | --- |
| `doc_id` | string | caller-supplied document identity |
| `title` | string | source title |
| `abstract` | string | text normalized and segmented by the pipeline |
| `categories` | string | source classification text |

`CleanDoc` carries the same fields after configured normalization. The pipeline
does not allocate a new document identity during cleaning.

## Retrieval Chunk

`ChunkWithoutEmbedding` is the segmentation contract. `Chunk` extends it with
an immutable embedding tuple.

| Field | Rule |
| --- | --- |
| `doc_id` | identifies the source record |
| `text` | contains the exact segmented text |
| `start`, `end` | integer source offsets; `start >= 0` and `end >= start` |
| `chunk_index` | non-negative ordinal within the source document |
| `title`, `category` | optional source context |
| `metadata` | read-only mapping for non-structural context |
| `embedding_spec` | optional dimensionality and model contract |
| `embedding` | final numeric vector, present on `Chunk` |
| `chunk_id` | SHA-256 identity derived from source ID, offsets, and text |

Metadata and the embedding specification do not participate in `chunk_id`.
Changing either may still change retrieval behavior, so an index fingerprint
must cover the full vector set and configuration rather than relying on chunk
IDs alone.

## Serialized Edge Model

The strict Pydantic `ChunkModel` is a versioned edge shape used by the
serialization adapters. Its contract is intentionally narrower:

```json
{
  "version": 1,
  "text": "a retrieval-ready passage",
  "metadata": {"source": "catalog.csv"},
  "embedding": [0.125, -0.25]
}
```

The model rejects unknown fields, coercion, empty text, non-finite vector
values, vectors longer than 8192 entries, and values outside the accepted
numeric range. `embedding` may be omitted; when present, it must be non-empty.
The computed text length is available in memory but excluded from canonical
serialization.

The core pipeline's retrieval `Chunk` and the edge `ChunkModel` serve different
purposes. The serialization adapters operate on the functional-programming
core chunk, not the retrieval chunk described above. `to_core_chunk()` retains
`text` and `metadata`; `from_core_chunk()` returns those same fields.
`embedding` is not transferred in either direction. Document identity, offsets,
ordinal, title, category, and embedding specification are outside this adapter.

## Identity and Projection Map

Every projection has a deliberate loss boundary:

| Transition | Preserved | Recomputed or changed | Not carried |
| --- | --- | --- | --- |
| `RawDoc` to `CleanDoc` | document ID, title, categories | normalized abstract | original abstract bytes |
| `CleanDoc` to retrieval chunk | document ID, selected text, source offsets | ordinal and `chunk_id` | unselected document text |
| unembedded to embedded chunk | all chunk fields | embedding tuple | nothing when the same chunk is enriched |
| `ChunkModel` to FP core chunk | text, metadata | core path becomes empty | embedding and retrieval identity |
| FP core chunk to `ChunkModel` | text, metadata | version defaults to `1` | path and embedding |

Only the first three transitions belong to the retrieval pipeline. The last two
are an edge-model interoperability path. Do not use that path to checkpoint a
retrieval chunk or to move vectors between systems.

## File Boundaries

The document CLI reads CSV records and writes one successful chunk per JSONL
line. Expected failures are returned or rendered separately; they are not
interleaved with successful rows in the output file. Treat the output as a
projection with an accompanying run context:

- write it to a new path or replace it atomically at the surrounding workflow;
- retain the input and effective configuration when reproducibility matters;
- validate every line and the expected row count before building an index; and
- do not infer an embedding model solely from vector length.

Expected boundary failures are represented with `Result` values. Unexpected
programming failures remain exceptions so corrupted or partial outputs are not
mistaken for successful domain results.

## Compatibility Rules

A change is compatibility-sensitive when it alters field meaning, stable ID
inputs, offset interpretation, serialization version, validation limits, or
the distinction between omitted and empty embeddings. Add a new version or an
explicit migration path for such changes; silently accepting both meanings
would make replay evidence ambiguous.

See [Execution Model](../architecture/execution-model.md) for how these values
move through the pipeline.
