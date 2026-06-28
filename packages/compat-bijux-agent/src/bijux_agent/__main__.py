"""Execute the canonical agent CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_agent.interfaces.cli.entrypoint import cli

if __name__ == "__main__":
    cli()
