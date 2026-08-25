"""Execute the canonical agent CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_agent.interfaces.cli.entrypoint import cli

from .compatibility import warn_compatibility


def main() -> None:
    """Warn and delegate to the canonical Agent command."""
    warn_compatibility()
    cli()


if __name__ == "__main__":
    main()
