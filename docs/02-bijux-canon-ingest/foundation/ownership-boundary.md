---
title: Ownership Boundary
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Ownership Boundary

Ingest authority is transformation authority. It decides how source material
becomes immutable documents, chunks, local indexes, ranked candidates, and
extractive citations under declared configuration.

```mermaid
flowchart TD
    change{"What invariant changes?"}
    representation["source representation"]
    vector["governed vector execution"]
    meaning["claim support or verification"]
    orchestration["role order or convergence"]
    authority["run acceptance or replay policy"]

    change --> representation
    change --> vector
    change --> meaning
    change --> orchestration
    change --> authority

    representation --> ingest["bijux-canon-ingest"]
    vector --> index["bijux-canon-index"]
    meaning --> reason["bijux-canon-reason"]
    orchestration --> agent["bijux-canon-agent"]
    authority --> runtime["bijux-canon-runtime"]
```

## Decision table

| Change | Owner | Reason |
| --- | --- | --- |
| normalize whitespace before chunk identity is computed | ingest | changes the prepared representation |
| alter overlap, tail handling, or structural deduplication | ingest | changes chunk boundaries, order, or identity |
| add a local lexical scoring option for the compact retrieval path | ingest | extends the package-owned reference workflow |
| select an eligible backend under exact/ANN and replay contracts | index | governs vector execution across backend capabilities |
| decide that cited bytes support a derived statement | reason | changes claim grounding and verification |
| retry a role because workflow convergence has not been reached | agent | changes orchestration lifecycle |
| permit or reject a completed flow under tenant policy | runtime | changes final run authority |

## The local retrieval seam

Both ingest and index contain retrieval-related code, but their authority is
different:

- ingest owns a local document workflow that makes preparation testable and
  provides BM25/NumPy reference retrieval and cited extraction;
- index owns explicit execution intent, artifact materialization, backend
  capability negotiation, exact or bounded ANN execution, and replay evidence.

Moving from the first to the second is not triggered by corpus size alone. The
boundary is crossed when retrieval needs governed backend choice, execution
contracts, cross-run identity, or replay semantics.

## Handoff contract

Downstream consumers receive stable source and chunk identity, normalized
text, offsets within that text, embeddings when configured, metadata, and
explicit result or failure values. They must not reinterpret normalized
offsets as original byte offsets or assume hash embeddings carry semantic
meaning.

The owner of a defect is the layer whose invariant was false. A changed chunk
caused by normalization belongs here; a correct chunk ranked incorrectly under
a declared vector contract belongs in index.

## Coordinate Spaces Are Part Of Custody

Cleaning can change case, whitespace, or retained content before chunking.
Chunk `start` and `end` therefore address the normalized `CleanDoc` text, not
the original CSV bytes or characters.

```mermaid
flowchart LR
    bytes["source bytes"]
    parsed["RawDoc fields"]
    normalized["CleanDoc text"]
    chunk["chunk text + normalized offsets"]
    candidate["ranked candidate"]

    bytes -->|decode and parse| parsed
    parsed -->|cleaning rules| normalized
    normalized -->|chunk geometry| chunk
    chunk -->|local retrieval| candidate
```

| Question | Evidence required |
| --- | --- |
| which source entered the pipeline? | source identifier plus retained input identity or digest |
| which text was segmented? | normalized parent text and effective cleaning configuration |
| where did a chunk come from? | parent identity, normalized offsets, chunk text, and geometry |
| can a citation be mapped to original bytes? | an explicit source-to-normalized mapping produced during preparation |

The current chunk contract does not carry a general source-byte mapping. A
consumer may quote the normalized span and identify its parent, but must not
claim original-byte coordinates unless it retained an independent mapping.
