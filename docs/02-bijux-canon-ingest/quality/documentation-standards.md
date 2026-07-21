---
title: Public Claim Standards
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Public Claim Standards

Claims about ingest are scoped by the evidence retained with a preparation
run. The package can establish structural and execution properties; it cannot
promote those properties into claims about source truth or semantic relevance.

```mermaid
flowchart LR
    source[Source record]
    config[Preparation configuration]
    chunks[Addressable chunks]
    index[Reference index]
    metrics[Recorded evaluation]

    source --> config --> chunks --> index --> metrics
```

## Claim vocabulary

| Public wording | Evidence required | Bound on the claim |
| --- | --- | --- |
| deterministic cleaning | identical normalized text for the same input and configuration | excludes caller-supplied or version-drifting cleaners |
| stable chunk identity | matching document identity, offsets, text, and resulting digest | changes when any identity input changes |
| ordered preparation | stable document and span order through the selected pipeline | does not imply distributed exactly-once delivery |
| validated embedding | vector dimension matches the declared specification | does not establish semantic usefulness |
| replayable preparation | source identity, configuration, adapter identity, and retained outputs are available | external services can still drift |
| retrieval baseline | metrics reproduce for the named corpus and model profile | does not generalize to another corpus or production model |
| citation retained | answer output resolves to a stored chunk and span | does not establish source authority or entailment |

## Artifact references

Commands and examples identify the files that carry the claim: source
descriptors, prepared records, saved-index envelopes, configuration, metrics,
and failure reports. A digest is described as an identity check, not as proof
of correctness. A schema is described as an interface contract, not as proof
that a deployment is available or secure.

## Limits remain visible

Reader-facing examples distinguish the document-oriented pipeline from the
minimal lazy pipeline, structural deduplication from semantic deduplication,
normalized string offsets from original byte offsets, and local reference
retrieval from governed indexing in `bijux-canon-index`.

When an optional model or application adapter enters the path, its name,
version, parameters, and failure behavior join the claim boundary. Omitting
that identity makes reproducibility unknown rather than implied.

See [invariants](invariants.md) for executable laws and
[risk register](risk-register.md) for the uncertainty that remains after those
laws pass.
