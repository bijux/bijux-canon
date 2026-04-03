# FAISS Vector Store

## Install

- `pip install bijux-vex[vdb]` (or `pip install faiss-cpu`)

## Connect

Use the explicit vector store flag:

```bash
python -m bijux_vex.boundaries.cli.app ingest \
  --doc "hello" --vector "[0.0,1.0,0.0]" \
  --vector-store faiss --vector-store-uri ./index.faiss
```

## Capabilities

- Exact search supported.
- ANN supported (experimental).
- Deletes supported (rebuild required if configured).

## Limitations

- Filtering is not supported.
- Requires local disk for index persistence.

## Recommended Use Cases

- Local, single-node workloads.
- Deterministic exact execution with stable storage.
- ND experiments when ANN is explicitly configured.

## Gotchas

- Index parameters must match execution mode.
- Rebuild after heavy delete workloads to avoid drift.

## Operational Tips

- Use `bijux vex vdb status` to inspect index metadata.
- Use `bijux vex vdb rebuild` after delete-heavy workloads.
