# End-to-End Tutorial

This tutorial is fully copy/pasteable. It shows an explicit, deterministic flow and an explicit VDB flow.

## Install

```
pip install bijux-canon-index
```

Optional extras:

```
pip install "bijux-canon-index[embeddings]"
pip install "bijux-canon-index[vdb]"
```

## Workflow A (BYO Vectors)

```bash
--8<-- "docs/examples/workflows/workflow_a.sh"
```

## Workflow B (Docs-Only + FAISS)

```bash
--8<-- "docs/examples/workflows/workflow_b.sh"
```

## Workflow C (ANN Bounded + Explain)

```bash
--8<-- "docs/examples/workflows/workflow_c.sh"
```

## Provenance

Workflow C includes `--explain` to show provenance output inline.
