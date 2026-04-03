# CLI Reference

The `bijux-llm-rag` CLI is built with Typer. Legacy alias: `bijux-rag`. Common commands:

- `bijux-llm-rag chunks --input docs.csv --output chunks.jsonl`
- `bijux-llm-rag index-build --input corpus.csv --out index.msgpack --backend bm25`
- `bijux-llm-rag retrieve --index index.msgpack --query "what is bm25?"`
- `bijux-llm-rag ask --index index.msgpack --query "..." --top-k 5`
- `bijux-llm-rag eval --suite tests/eval --index index.msgpack --baseline tests/eval/baselines/bm25/default/metrics.json`

Typer auto-generates `--help`; run `bijux-llm-rag --help` or subcommand `--help` for parameter details.
