# Qdrant Vector Store

## Install

- `pip install bijux-vex[vdb]` (or `pip install qdrant-client`)

## Connect

```bash
python -m bijux_vex.boundaries.cli.app ingest \
  --doc "hello" --vector "[0.0,1.0,0.0]" \
  --vector-store qdrant --vector-store-uri http://localhost:6333
```

## Capabilities

- Exact and ANN supported (remote).
- Deletes supported.
- Filtering supported via adapter options.

## Limitations

- Requires a running Qdrant instance.
- Consistency is backend-dependent (see capabilities output).

## Recommended Use Cases

- Remote, shared vector storage.
- Workloads that need filtering or metadata queries.
- ANN at scale with explicit budgets.

## Gotchas

- Network latency affects ND budgets.
- Ensure credentials are redacted in logs and provenance.

## Operational Tips

- Use `bijux vex vdb status` to validate connectivity.
- Configure batch sizes and retries via adapter options.
