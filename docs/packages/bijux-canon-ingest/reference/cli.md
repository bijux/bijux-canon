# CLI Reference

`bijux-canon-ingest` exposes one executable: `bijux-canon-ingest`.

Common commands:

- `bijux-canon-ingest index build --input corpus.csv --out index.msgpack --backend bm25`
- `bijux-canon-ingest retrieve --index index.msgpack --query "what is bm25?"`
- `bijux-canon-ingest ask --index index.msgpack --query "..." --top-k 5`
- `bijux-canon-ingest eval --suite tests/eval --index index.msgpack --baseline tests/eval/baselines/bm25/default/metrics.json`

Run `bijux-canon-ingest --help` or any subcommand with `--help` for details.
