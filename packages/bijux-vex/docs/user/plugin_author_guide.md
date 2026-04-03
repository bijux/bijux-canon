# Plugin Author Guide

## Template Layout

```
template_plugin/
  pyproject.toml
  src/
    bijux_vex_plugin_example/
      __init__.py
  tests/
    test_plugin_contracts.py
```

## Entry Points

Register entrypoints under:

- `bijux_vex.vectorstores`
- `bijux_vex.embeddings`
- `bijux_vex.runners`

## Test Kit

Run the plugin test kit:

```bash
python scripts/plugin_test_kit.py --format json
```

## Minimal Contract Requirements

- Declare determinism.
- Declare randomness sources.
- Declare approximation behavior.
