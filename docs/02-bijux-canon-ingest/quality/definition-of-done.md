---
title: Release Acceptance
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-22
---

# Release Acceptance

An ingest change is releasable when the prepared corpus remains identifiable,
ordered, inspectable, and honest about partial failure. Passing transformation
tests alone is insufficient when the change also affects a public envelope,
persisted index, citation span, or retrieval claim.

```mermaid
flowchart LR
    change[Changed ingest behavior]
    law[Owning value or stage law]
    boundary[Crossed public boundary]
    artifact[Retained artifact comparison]
    claim[Bounded release claim]
    accept[Release candidate]

    change --> law --> boundary --> artifact --> claim --> accept
```

## Acceptance record

| Changed surface | Required evidence | Release-blocking result |
| --- | --- | --- |
| cleaning or source identity | normalized-text fixtures, repeated identity comparison, and source metadata | equivalent configuration produces unexplained identity drift |
| chunking or tail policy | span, overlap, ordering, and boundary fixtures | a citation cannot be resolved against the retained normalized text |
| embedding contract | model and dimension validation plus adapter identity | vectors are accepted without a compatible `EmbeddingSpec` |
| streaming or concurrency | ordering, termination, backpressure, and partial-failure evidence | loss or duplication can be reported as complete success |
| deduplication | structural-key and stable-order fixtures | winner selection depends on incidental iteration order |
| persisted index or cache | round trip, version mismatch, and stale-state rejection | incompatible state is silently reused |
| CLI or HTTP envelope | focused interface test, schema drift check, and error mapping | an adapter changes domain success or failure meaning |
| retrieval-quality claim | checked-in corpus, metric output, configuration, and model identity | a deterministic hash baseline is presented as semantic quality |

## Minimum release packet

The acceptance record is reviewable only when its inputs and outcomes remain
joined. Retain this packet for the affected corpus or fixture:

| Record | Required contents | Why it belongs in the packet |
| --- | --- | --- |
| source inventory | document identifiers, source descriptors, input digest, accepted and rejected counts | establishes what was offered to preparation |
| normalized configuration | cleaning rules, safeguards, chunk geometry, tail policy, embedder and storage choices | makes behavior independent of a mutable filename or environment default |
| preparation output | clean-record identity, chunks, parent links, offsets, and serialization version | lets a reviewer resolve downstream material back to prepared text |
| execution observations | stage order, timings where relevant, retry and breaker decisions, cache disposition | exposes behavior that output bytes alone cannot explain |
| failure inventory | stable error type, stage, source position, cause, retry state, and terminal disposition | prevents rejected work from disappearing into success counts |
| comparison result | prior-versus-candidate identities, changed records, expected drift, and unexplained drift | distinguishes an intentional contract change from accidental corpus movement |

`packages/bijux-canon-ingest/tests/invariants/` protects cross-cutting laws;
the processing, streaming, retrieval, storage, interface, and safeguard unit
suites protect their owned mechanisms. An end-to-end fixture joins those
surfaces for one declared workflow. No single lane substitutes for the packet:
a unit test may prove a transformation law while saying nothing about the
serialized corpus handed to a consumer.

## Reverse-audit requirement

Select at least one emitted candidate or citation and walk it backward through
chunk identity, offsets, normalized parent, configuration, and source record.
Then select at least one rejected input and walk its terminal error forward to
the reported summary. Release is blocked if either path requires guessing,
reconstructing discarded configuration, or treating absence as success.

## Evidence custody

Keep the input identifiers, normalization and chunking configuration, produced
chunk records, embedding specification, observations, errors, and evaluation
summary together. A final count or saved index without its preparation
configuration cannot explain later ranking or citation drift.

Expected failures remain part of the acceptance record. Rejected documents,
truncated streams, breaker openings, and retry exhaustion must retain stage,
position, cause, and termination status rather than disappearing into an empty
result.

## Release decision

Acceptance is package-specific and claim-specific:

- transformation evidence supports deterministic preparation claims;
- persistence evidence supports round-trip and compatibility claims;
- offline evaluation supports only the recorded corpus, model, and metrics;
- none of these establishes source accuracy, licensing, or deployment safety.

Use [change validation](change-validation.md) to select the narrowest checks and
[known limitations](known-limitations.md) to preserve unsupported boundaries in
the release description.
