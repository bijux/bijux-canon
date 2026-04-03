# bijux-rag

`bijux-rag` is a compatibility package that installs `bijux-canon-ingest` and
preserves the legacy `bijux_rag` Python import surface.

Use the canonical package for new installs:

```bash
pip install bijux-canon-ingest
```

The legacy command name `bijux-rag` remains available as an alias after installation.
The legacy Python import `import bijux_rag` also remains available through this package.
