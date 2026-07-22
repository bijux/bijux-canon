---
title: Interpreting Preparation Evidence
audience: mixed
type: reference
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-22
---

# Interpreting Preparation Evidence

An ingest result is evidence of a declared transformation, not certification of
the source or the downstream decision. Interpret it by following the retained
source identity, configuration, transformations, output records, and terminal
observations together.

```mermaid
flowchart LR
    source["source descriptor + digest"]
    config["preparation configuration"]
    stages["clean + chunk + embed + deduplicate"]
    records["prepared records + identities"]
    observations["counts + failures + metrics"]

    source --> config --> stages --> records --> observations
```

## Read One Preparation Result

| Review question | Evidence to retain | Failure if missing |
| --- | --- | --- |
| Which input was admitted? | source URI or record key, content digest, reader and adapter identity | a later run cannot distinguish source drift from transformation drift |
| Which text was transformed? | normalized-text digest and cleaning configuration | chunk spans cannot be related to the exact normalized text |
| How were chunks created? | chunking parameters, tail policy, order, offsets, chunk identities | matching prose may conceal different segmentation |
| Which vectors were produced? | embedder, model or implementation revision, dimension, device and parameters | vector compatibility and reproducibility are unknown |
| What was removed? | deduplication rule, input/output counts, rejection or observation records | absence can be mistaken for source absence |
| What was published? | saved-index envelope or output artifact, schema version, fingerprint, terminal status | partially written state can look complete |

## Bounded Claim Vocabulary

| Claim | Required evidence | Bound on the claim |
| --- | --- | --- |
| deterministic cleaning | identical normalized text for the same input, implementation, and configuration | caller-supplied or version-drifting cleaners join the boundary |
| stable chunk identity | matching document identity, offsets, text, parameters, and digest | any identity-bearing input can change the result |
| ordered preparation | stable document and span order through the selected pipeline | does not imply distributed exactly-once delivery |
| validated embedding | vector shape and dimension match the declared specification | does not establish semantic usefulness |
| replayable preparation | source, configuration, adapter identity, and retained outputs remain available | external services and mutable source systems can still drift |
| retrieval baseline | metrics reproduce for the named corpus, query set, and model profile | does not generalize to another corpus or production model |
| citation retained | answer output resolves to a stored chunk and span | does not establish source authority or entailment |

## Interpret Identity Correctly

A digest detects identity or change; it does not prove correctness. A schema
defines an accepted representation; it does not prove that an HTTP service is
deployed. A deterministic hash embedder is a repeatable reference profile; it
does not measure semantic retrieval quality. A citation resolves an answer to
a chunk; it does not prove that the chunk supports the answer.

Offsets refer to normalized Python strings unless an artifact explicitly
retains original byte positions. Structural deduplication compares the selected
record equality or key; it does not find paraphrases or copied ideas. BM25 and
NumPy cosine scores belong to different ranking models and must not be compared
as a shared confidence scale.

## Optional Integrations Widen The Boundary

When a model, source reader, storage adapter, clock, caller-supplied stage, or
application service enters the path, retain its name, version, configuration,
failure behavior, and relevant external state. If any of those identities is
absent, reproducibility is unknown rather than implied by the package's local
deterministic stages.

Continue with [invariants](invariants.md) for machine-enforced laws,
[known limitations](known-limitations.md) for boundaries that remain after
those laws pass, and the [risk register](risk-register.md) for failure signals
and controls.
