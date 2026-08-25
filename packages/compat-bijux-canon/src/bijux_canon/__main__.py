"""Execute the canonical runtime CLI through the compatibility package name."""

from __future__ import annotations

from bijux_canon_runtime.interfaces.cli.entrypoint import main as canonical_main

from .compatibility import warn_compatibility


def main() -> int:
    """Warn and delegate to the canonical Runtime command."""
    warn_compatibility()
    return canonical_main()


if __name__ == "__main__":
    raise SystemExit(main())
