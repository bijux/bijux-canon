---
title: Operator Workflows
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-ingest-docs
last_reviewed: 2026-07-21
---

# Operator Workflows

This workflow produces a reviewable corpus, inspects retrieval behavior, and
publishes only after the source, configuration, index, and evaluation evidence
agree.

## Prepare the Source Contract

Use a UTF-8 CSV with stable document IDs. For the direct index path, the reader
expects `doc_id`, `title`, `abstract`, and `categories`. Do not use row numbers
as IDs: sorting or filtering the file would change downstream identity.

Pin the preparation policy in JSON:

```json
{
  "steps": [
    {"name": "clean", "params": {}},
    {
      "name": "chunk",
      "params": {
        "chunk_size": 384,
        "overlap": 48,
        "tail_policy": "emit_short"
      }
    },
    {"name": "embed", "params": {}}
  ]
}
```

## Produce Inspectable Chunks

```bash
mkdir -p artifacts/ingest

bijux-canon-ingest documents.csv \
  --config pipeline.json \
  --out artifacts/ingest/chunks.jsonl
```

Inspect the row count, empty embeddings, unexpectedly short tails, and metadata
before indexing. The pipeline writer emits successful rows only, so reconcile
the file with the command outcome rather than using row count as the sole
success signal.

## Build and Identify the Index

```bash
bijux-canon-ingest index build \
  --input documents.csv \
  --out artifacts/ingest/corpus.index \
  --backend bm25 \
  --chunk-size 384 \
  --overlap 48 \
  --tail-policy emit_short \
  > artifacts/ingest/index-build.json
```

Retain the printed fingerprint. It identifies the built scoring state; it does
not replace the source or configuration. Use a fresh output path when changing
backend, chunk policy, embedder, or source data.

## Inspect Before Answering

```bash
bijux-canon-ingest retrieve \
  --index artifacts/ingest/corpus.index \
  --query "retention period" \
  --top-k 5 \
  --out artifacts/ingest/candidates.json
```

Review candidate text, document identity, chunk identity, score direction, and
filters. Only then run the extractive answer path:

```bash
bijux-canon-ingest ask \
  --index artifacts/ingest/corpus.index \
  --query "How long are signed records retained?" \
  --top-k 5 \
  --out artifacts/ingest/answer.json
```

Every citation should resolve to a returned chunk. An answer without a usable
citation is not an acceptable retrieval handoff.

## Gate Retrieval Changes

Create `evaluation/retention/queries.jsonl` with query and relevant-document
sets, then compare the candidate index with the retained baseline:

```bash
bijux-canon-ingest eval \
  --index artifacts/ingest/corpus.index \
  --suite evaluation/retention \
  --k 10 \
  --baseline evaluation/retention/baseline.json \
  --tolerance 0.01 \
  > artifacts/ingest/evaluation.json
```

Treat an allowed decline as a review decision, not an invisible pass. Record
why the tolerance is scientifically or operationally acceptable.

## Publish the Handoff

Publish the following as one governed set:

- source dataset identity and schema;
- effective cleaning, chunking, and embedding configuration;
- chunk JSONL when downstream consumers require inspectable records;
- index artifact, backend, and fingerprint;
- candidate inspection and evaluation result;
- command status and structured failures; and
- dependency/model identity for non-built-in embedders.

Do not publish a partially written file, an index whose fingerprint was not
captured, or an answer whose citations were not resolved.
