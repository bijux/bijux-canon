# CLI Reference

The `bijux-rag` CLI is built with Typer. Common commands:

- `bijux-rag chunks --input docs.csv --output chunks.jsonl`
- `bijux-rag index-build --input corpus.csv --out index.msgpack --backend bm25`
- `bijux-rag retrieve --index index.msgpack --query "what is bm25?"`
- `bijux-rag ask --index index.msgpack --query "..." --top-k 5`
- `bijux-rag eval --suite tests/eval --index index.msgpack --baseline tests/eval/baselines/bm25/default/metrics.json`

Typer auto-generates `--help`; run `bijux-rag --help` or subcommand `--help` for parameter details.
