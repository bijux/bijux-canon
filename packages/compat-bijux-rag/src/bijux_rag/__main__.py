"""Execute the canonical ingest CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_ingest.interfaces.cli.entrypoint import main as canonical_main

from .compatibility import warn_compatibility


def main() -> int:
    """Warn and delegate to the canonical Ingest command."""
    warn_compatibility()
    return canonical_main()


if __name__ == "__main__":
    raise SystemExit(main())
