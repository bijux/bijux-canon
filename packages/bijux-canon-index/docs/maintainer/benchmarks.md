# Benchmark Runs

See `docs/maintainer/benchmark_truth_table.md` for what each benchmark measures and does not claim.

## Baselines
- Baselines live under `benchmarks/baselines/`.
- The CI matrix expects entries for memory, FAISS, and Qdrant (exact + ann).
 - Replace `status: todo` placeholders after running on a dedicated host.

## Run Locally
```bash
make install
.venv/bin/python -m bijux_vex.boundaries.cli.app bench --store vdb --vector-store faiss --mode exact
.venv/bin/python -m bijux_vex.boundaries.cli.app bench --store vdb --vector-store faiss --mode ann
```

## Qdrant (Local)
Qdrant benchmarks can run without Docker using the in-memory client:
```bash
.venv/bin/python -m bijux_vex.boundaries.cli.app bench --store vdb --vector-store qdrant --vector-store-uri :memory: --mode exact
.venv/bin/python -m bijux_vex.boundaries.cli.app bench --store vdb --vector-store qdrant --vector-store-uri :memory: --mode ann
```

## Qdrant (Docker)
If you prefer a local service:
```bash
docker run --rm -p 6333:6333 qdrant/qdrant:latest
```
Then run the same commands without `--vector-store-uri :memory:`.
## TODOs
- TODO: generate FAISS exact/ann baselines on a faster host.
- TODO: generate Qdrant exact/ann baselines on a faster host.
- TODO: generate FAISS 100k baselines on a faster host.
