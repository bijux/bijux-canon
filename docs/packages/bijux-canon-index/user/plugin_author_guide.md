# Plugin Author Guide

## Template Layout

```
template_plugin/
  pyproject.toml
  src/
    bijux_canon_index_plugin_example/
      __init__.py
  tests/
    test_plugin_contracts.py
```

## Entry Points

Register entrypoints under:

- `bijux_canon_index.vectorstores`
- `bijux_canon_index.embeddings`
- `bijux_canon_index.runners`

## Test Kit

Run the plugin test kit:

```bash
PYTHONPATH=packages/bijux-canon-dev/src python -m bijux_canon_dev.packages.index.plugin_contract_report --format json
```

## Minimal Contract Requirements

- Declare determinism.
- Declare randomness sources.
- Declare approximation behavior.
