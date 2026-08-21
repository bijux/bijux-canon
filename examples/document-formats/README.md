# Parser qualification sources

This portfolio defines the seven real documents used to qualify the ingestion
adapters. It is deliberately separate from the ancient-DNA research corpus:
these documents establish parser and locator behavior, not research relevance.

`sources.jsonl` is the durable source policy. Each line records canonical
metadata, an exact acquisition endpoint, license evidence, redistribution
terms, format-specific admission requirements, and the independent locator
truth that must be authored before admission. `media/`, `sources/`, and
`acquisition-receipts/` contain the immutable, reviewed acquisition outputs.
The PLOS HTML source is a declared deterministic extraction of the licensed
article body and citation metadata; publisher interface code, global chrome,
and embedded images are not stored.

Replaying the acquisition command is offline and byte-stable when all durable
receipts exist:

```console
python -m bijux_canon_dev.corpus.parser_sources \
  --portfolio examples/document-formats/sources.jsonl \
  --output-root examples/document-formats
```

`corpus.lock.json` binds every reviewed source to its media type, byte count,
SHA-256 digest, license, attribution, retrieval time, declared transformations,
and acquisition evidence. Rebuild or verify it from the same durable inputs:

```console
python -m bijux_canon_dev.corpus.parser_lock \
  --portfolio examples/document-formats/sources.jsonl \
  --output-root examples/document-formats \
  --lock examples/document-formats/corpus.lock.json
```

`locator-truth.jsonl` is an independently selected, identity-bound review set.
It covers every required semantic role with exact text and SHA-256 digests for
the six admitted formats, plus a typed full-image OCR refusal without invented
text. Validate its page, DOM, line, XML, and OOXML locators against the lock:

```console
python -m bijux_canon_dev.corpus.parser_locator_truth \
  --portfolio examples/document-formats/sources.jsonl \
  --output-root examples/document-formats \
  --lock examples/document-formats/corpus.lock.json \
  --truth examples/document-formats/locator-truth.jsonl
```

Generated download logs and verification evidence are disposable and remain
under the ignored repository `artifacts/` directory. They are never source
inputs and are never tracked by Git.
