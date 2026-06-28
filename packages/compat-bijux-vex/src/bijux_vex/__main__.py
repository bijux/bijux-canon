"""Execute the canonical index CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_index.interfaces.cli.app import app


if __name__ == "__main__":
    app()
