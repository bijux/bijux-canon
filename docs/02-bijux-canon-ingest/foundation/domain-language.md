---
title: Domain Language
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Domain Language

Ingest turns source documents into deterministic retrieval material. Its
vocabulary separates source identity, text transformation, vector generation,
and downstream search so that a “successful ingest” cannot hide a changed
corpus.

## Source and Preparation

| Term | Meaning |
| --- | --- |
| source document | caller-owned record before package processing |
| `RawDoc` | source row with `doc_id`, title, abstract, and categories |
| `CleanDoc` | document after deterministic normalization; it retains `doc_id` |
| cleaning | text normalization that may change content before offsets are assigned |
| document identity | stable caller-supplied `doc_id`, independent of row position |
| prepared input | validated, normalized material ready for chunking or handoff |

Cleaning is not parsing, retrieval, or reasoning. A parser decides whether a
source row is admissible. Cleaning transforms admitted text. Neither operation
decides whether a later answer is correct.

## Chunking and Embedding

| Term | Meaning |
| --- | --- |
| chunk | a span of normalized document text with source offsets and ordinal |
| chunk identity | SHA-256 derived from `doc_id`, offsets, and chunk text |
| chunk size | maximum text-window size selected by the chunking policy |
| overlap | text shared by adjacent windows; always smaller than chunk size |
| tail policy | treatment of the final short span: emit, drop, or pad |
| embedding | numeric representation attached to a chunk |
| embedding specification | model, dimension, metric, and normalization contract |

Offsets refer to the normalized text received by the chunker, not necessarily
the original source bytes. An embedding vector without its specification is
incomplete evidence because dimension alone does not identify the model or
normalization policy.

## Retrieval Terms

| Term | Meaning |
| --- | --- |
| retrieval index | persisted BM25 or NumPy-cosine search state built from chunks |
| index fingerprint | identity of ordered chunks, backend configuration, and scoring state |
| candidate | one ranked chunk with a score and retrieval metadata |
| filter | exact metadata or document-identity constraint applied during retrieval |
| extractive answer | answer assembled from retrieved text rather than open-ended generation |
| citation | answer reference back to the supporting chunk identity |
| evaluation suite | query records with relevant document IDs used to compute recall at k |

The local `ask` command is retrieval plus extractive answer assembly. It is not
a reasoning agent. Likewise, `hash16` is a deterministic embedding useful for
contract checks; it is not a semantic language model.

## Handoffs

A **chunk handoff** transfers prepared records to a downstream indexer. An
**index handoff** transfers backend-specific search state. A **run context** is
the source identity, effective configuration, process outcome, and model
identity required to interpret either artifact.

Use “reproducible” only when the run context is retained and the artifact can be
rebuilt or loaded under the same contract. Use “deterministic” for behavior
whose output is fixed by declared inputs; it does not mean the output is
scientifically correct or operationally complete.
