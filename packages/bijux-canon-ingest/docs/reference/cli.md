# CLI Reference

The `bijux-canon-ingest` CLI is built with Typer. Legacy alias: `bijux-rag`. Common commands:

- `bijux-canon-ingest chunks --input docs.csv --output chunks.jsonl`
- `bijux-canon-ingest index-build --input corpus.csv --out index.msgpack --backend bm25`
- `bijux-canon-ingest retrieve --index index.msgpack --query "what is bm25?"`
- `bijux-canon-ingest ask --index index.msgpack --query "..." --top-k 5`
- `bijux-canon-ingest eval --suite tests/eval --index index.msgpack --baseline tests/eval/baselines/bm25/default/metrics.json`

Typer auto-generates `--help`; run `bijux-canon-ingest --help` or subcommand `--help` for parameter details.
