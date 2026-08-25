"""Compatibility notice for the preserved ``bijux-canon`` identity."""

from __future__ import annotations

import warnings

MESSAGE = (
    "bijux-canon is a compatibility name; use bijux-canon-runtime, import "
    "bijux_canon_runtime, and invoke bijux-canon-runtime for canonical behavior"
)
_WARNED = False


def warn_compatibility(*, stacklevel: int = 2) -> None:
    """Emit the process-local compatibility notice once."""
    global _WARNED
    if _WARNED:
        return
    _WARNED = True
    warnings.warn(MESSAGE, FutureWarning, stacklevel=stacklevel)


__all__ = ["MESSAGE", "warn_compatibility"]
