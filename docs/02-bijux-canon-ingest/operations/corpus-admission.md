---
title: Corpus Admission
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-08-21
---

# Corpus Admission

A document is real-corpus evidence only after its source, rights, bytes,
parsing result, and independently reviewed truth have passed separate recorded
decisions. A URL, downloaded file, parser success, fixture, generated paragraph,
or system-produced label is not an admitted corpus.

## Admission States

Corpus records move through explicit states. Each transition appends a receipt;
it does not overwrite an earlier decision.

```text
identified -> metadata_verified -> license_reviewed -> acquired
           -> checksummed -> parsed -> truth_annotated -> admitted
           -> held_out -> published
```

`superseded` may follow any retained state when a corrected source, license
decision, parser contract, or truth set replaces it. A failed transition keeps
the last accepted state and records a typed rejection. No state is inferred
from the existence of a later-looking file.

| State | Decision and required evidence | Owner |
| --- | --- | --- |
| `identified` | stable source ID, DOI or canonical URI, candidate format, and discovery provenance | curator |
| `metadata_verified` | title, authors, journal or publisher, publication year, canonical landing page, and identifier agree with an authoritative record | curator |
| `license_reviewed` | the license for this exact work and version permits the planned acquisition, transformation, storage, evaluation, and redistribution | license reviewer |
| `acquired` | retrieval timestamp, response identity, media type, byte count, acquisition command, and protected local relative path identify the materialized bytes | acquisition operator |
| `checksummed` | a cryptographic digest binds the exact bytes; content checks reject abstracts, login pages, error pages, and unexpected media | admission automation |
| `parsed` | a qualified parser emits source-faithful text, stable document identity, exact locator mappings, structured rejects, and transformation provenance | ingest maintainer |
| `truth_annotated` | independent reviewers record locators, graded qrels, claims, citation relations, conflict and abstention labels, adjudication, and reviewer provenance | truth-review team |
| `admitted` | all required prior receipts agree, limitations are explicit, and the snapshot manifest locks content, parser, truth, configuration, and split identities | admission authority |
| `held_out` | the case assignment was frozen before final tuning and its labels are access-controlled from prompt, parameter, reranking, threshold, and selection work | evaluation custodian |
| `published` | only redistribution-permitted bytes and approved metadata, acquisition recipes, hashes, truth, and attribution are included in the declared publication | publication reviewer |
| `superseded` | the replacement identity and reason are recorded without deleting the historical bytes, decisions, or evaluation lineage | admission authority |

Discovery, review, acquisition, and admission must use different event types
even when one operator performs more than one role. This preserves the question
each decision answered and prevents an acquisition success from masquerading as
legal approval.

## Source And Rights Record

Every candidate source record includes:

- stable source ID, DOI or canonical URI, title, authors, journal or publisher,
  publication year, and canonical landing page;
- retrieval timestamp, acquisition method, final resolved URI, media type,
  byte count, byte hash, and corpus-root-relative storage path;
- exact license expression, license URL, attribution text, access terms,
  redistribution terms, and the evidence used for the decision;
- transformations applied to the acquired bytes and the tool, version,
  configuration, and output hash for each transformation; and
- known limitations, sensitive-content classification, disclosure controls,
  and any prohibition on committing or publishing the bytes.

License review applies to the exact article and materialized version. Publisher,
journal, collection, or historical defaults do not establish the license of an
individual work. When redistribution is not permitted, retain protected local
bytes and publish only lawful metadata, acquisition instructions, checksums,
and evaluation records that do not disclose restricted content.

## Acquisition And Materialization

Acquisition is a network-enabled, policy-bound operation. It must reject
redirects outside approved origins, authentication or error pages, media-type
mismatches, excessive size, archive expansion beyond declared bounds, and
content whose hash or identity conflicts with an existing source record.

The admitted snapshot is immutable and later runs offline. Materialization
therefore retains the exact bytes rather than depending on a live URL during
parsing, indexing, evaluation, inspect, or replay. A changed upstream document
creates a new source-byte identity and snapshot generation; it does not mutate
the admitted generation.

The flagship ancient-DNA portfolio requires full-text JATS for each specified
PLOS article. An abstract, citation export, landing page, or publisher error
body is a typed acquisition rejection. Parser qualification for digital PDF,
HTML, Markdown, plain text, and DOCX uses separately lawful real documents.
Image-only or scanned material returns an `ocr_required` refusal until an OCR
implementation and its provenance contract are separately admitted.

## Parsing Admission

A parser result qualifies only when it preserves:

1. source byte identity and parser/configuration identity;
2. source-faithful normalized text with every transformation declared;
3. exact locators capable of resolving a chunk or citation back to immutable
   source text and its hash;
4. deterministic document and chunk identities independent of absolute paths,
   timestamps, and process IDs; and
5. explicit rejects for unsupported, malformed, encrypted, oversized,
   expansion-heavy, or OCR-required input.

Success on a sample fixture does not admit a format. Qualification includes
real documents, malformed and boundary cases, deterministic repetition, and a
restart from retained bytes and configuration.

## Independent Truth

Truth is authored without copying or approving system output. Each evaluation
case records the source snapshot and exact locators, graded qrels, expected and
optional atomic claims, opposed and forbidden claims, claim-citation support or
opposition relations, conflict expectations, abstention expectations, and the
allowed agent-policy outcome.

At least 120 manually reviewed cases are stratified by source, question type,
evidence density, conflict, abstention, and retrieval difficulty. Two reviewers
and an adjudication record resolve disagreements. Numerators, denominators,
excluded cases, and label changes remain auditable.

Development and held-out assignments are frozen before final tuning. Held-out
labels cannot influence prompts, model or index parameters, fusion and
reranking, thresholds, budgets, or case selection. Access to held-out labels is
recorded, and any premature disclosure invalidates the affected held-out
evaluation generation.

## Fixtures And Synthetic Material

Fixtures and synthetic text are useful for parser branches, serialization,
failure injection, fuzzing, and deterministic unit contracts. They never
satisfy a real-corpus, parser-qualification, retrieval-quality, grounding,
flagship, or publication claim. Derived or transformed real text is still not
independent truth when labels come from the system under evaluation.

Reports classify every input as `real_admitted`, `real_not_admitted`,
`fixture`, or `synthetic` and fail closed when a production metric includes an
ineligible class.

## Admission Decision

An admission manifest binds the source records, byte hashes, license receipts,
parser outputs, locator validation, truth generation, split manifest,
limitations, and governing tool and configuration locks. Admission fails when
any required receipt is absent, stale, mismatched, or produced from a different
source generation.

The accepted manifest publishes counts for candidates, each state, typed
rejections, admitted documents, truth cases, and held-out cases. A nonzero file
count or successful command exit is not an admission criterion. Downstream
index, reason, agent, and runtime evidence identifies the exact admitted
snapshot; mixing generations invalidates the run.

## Publication Review

Publication is a new decision, not an automatic consequence of admission. The
reviewer verifies redistribution rights for every published byte, required
attribution, privacy and sensitive-content handling, license compatibility of
the aggregate, reproducible acquisition instructions, checksum completeness,
and separation of held-out labels.

The publication record lists omitted restricted sources and explains how an
authorized evaluator can rematerialize them. Superseded versions remain
addressable for historical replay but are excluded from current capability and
quality claims.
