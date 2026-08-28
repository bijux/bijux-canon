"""Execute the canonical index CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_index.interfaces.cli.app import app

from .compatibility import warn_compatibility


def main() -> None:
    """Warn and delegate to the canonical Index command."""
    warn_compatibility()
    app()


if __name__ == "__main__":
    main()
