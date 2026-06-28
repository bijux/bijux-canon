"""Execute the canonical ingest CLI through the legacy package name."""

from __future__ import annotations

from bijux_canon_ingest.interfaces.cli.entrypoint import main


if __name__ == "__main__":
    raise SystemExit(main())
