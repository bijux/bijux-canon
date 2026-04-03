# Tests & Eval

- **Unit/Property**: `make test` runs unit + property-based suites with coverage to `artifacts/bijux-rag/test`.
- **E2E quality gates**: 25 pinned queries × 4 assertions (100 tests) exercising index→retrieve→ask deterministically.
- **Eval assets**: `tests/eval/corpus.jsonl`, `tests/eval/queries.jsonl`, plus baselines under `tests/eval/baselines/`.
- **Baselines**: generated via `make eval-baseline` (BM25 CI profile); CI gates regressions via recall/MRR/nDCG and grounding checks.
- **API fuzz**: `make api` runs Schemathesis against `../../apis/bijux-rag/v1/schema.yaml`.
- **Artifacts**: coverage XML/HTML in `artifacts/bijux-rag/test`, junit in `artifacts/bijux-rag/test/junit.xml`.
