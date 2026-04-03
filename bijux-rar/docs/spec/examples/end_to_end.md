
## Minimal End-to-End Example
STATUS: EXPLANATORY

Trace schema version: 1 (this example is valid for schema_version=1; newer versions require migration if fields change).

Input:
- ProblemSpec: "What is Rust?", preset: "default", seed: 0, corpus: tests/fixtures/corpus_small.jsonl

Generated artifacts (under `artifacts/runs/<run_id>/`):
- `spec.json`, `plan.json`, `trace.jsonl`, `manifest.json`, `verify.json`, `provenance/corpus.jsonl`, `provenance/index/bm25_index.json`

Trace snippet (claim event):
- `claim_emitted` with statement containing `[evidence:<id>:<b0>-<b1>:<sha256>]`

Verification output:
- `verify.json` with `failures: []`, checks all passed.

Replay:
- `replay/trace.jsonl` fingerprint matches original when corpus/index/provenance unchanged.

What breaks if schema_version changes:
- Trace fields may differ; replay/verify will reject until migrated.
- Manifest/provenance hashes must be regenerated for the new schema.

Broken run (intentional failure):
- Delete one evidence file after manifest generation.
- Run `bijux-rar verify --trace trace.jsonl --plan plan.json --fail-on-verify`.
- Expected: verifier fails `support_span_hashes` with missing file/hash mismatch; run is invalid.***
