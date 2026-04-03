# Blessed Workflows

These are the three supported "blessed workflows." Each has a single copy/paste script that runs end-to-end.

Note: Workflows B and C require the FAISS backend (`pip install faiss-cpu`).

## Preflight Checks

- Validate inputs/config before ingest: `bijux vex validate --doc "text" --vector "[0.0,1.0]" --vector-store memory`
- Diagnose setup: `bijux vex doctor --vector-store faiss --vector-store-uri index.faiss`

## Workflow A: BYO Vectors → Memory → Exact Execute

```bash
--8<-- "docs/examples/workflows/workflow_a.sh"
```

## Workflow B: Docs-Only → Explicit Embed Model → FAISS → Execute

```bash
--8<-- "docs/examples/workflows/workflow_b.sh"
```

## Workflow C: ANN Bounded → Provenance + Explain

```bash
--8<-- "docs/examples/workflows/workflow_c.sh"
```

## Realistic Demo App

```bash
python docs/examples/demo_app.py
```
