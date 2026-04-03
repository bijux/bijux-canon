# bijux-agent

`bijux-agent` is a compatibility package that installs `bijux-canon-agent`.
It also preserves the legacy `bijux_agent` Python import surface.

Use the canonical package for new installs:

```bash
python -m pip install bijux-canon-agent
```

The legacy command name `bijux-agent` remains available as an alias after installation.
The legacy Python import `import bijux_agent` also remains available through this package.
