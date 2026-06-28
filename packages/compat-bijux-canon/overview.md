# bijux-canon

Use this package only when an existing environment still expects the shorter
family-root runtime name. Each release continues the published `bijux-canon`
distribution and installs `bijux-canon-runtime` at the same version.

The canonical runtime owner remains `bijux-canon-runtime`. This package exists
only to preserve the shorter install, import, and command names.

## What it does

- installs the canonical runtime package `bijux-canon-runtime`
- pins that canonical runtime package to the same published version
- preserves the `bijux_canon` Python import surface
- preserves the `bijux-canon` command name

## Preferred install for new environments

```bash
uv add bijux-canon-runtime
```

## Migration guidance

If you are updating scripts or dependencies, prefer changing them to:

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- compatibility package handbook: `https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-canon/`
- docs entrypoint: `https://bijux.io/bijux-canon/bijux-canon-runtime/`
- migration handbook: `https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/`
