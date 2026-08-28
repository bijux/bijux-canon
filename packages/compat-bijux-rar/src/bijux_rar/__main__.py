"""Execute the canonical reason CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_reason.interfaces.cli import app

from .compatibility import warn_compatibility


def main() -> None:
    """Warn and delegate to the canonical Reason command."""
    warn_compatibility()
    app()


if __name__ == "__main__":
    main()
