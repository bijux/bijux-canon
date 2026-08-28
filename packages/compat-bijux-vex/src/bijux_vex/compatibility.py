"""Compatibility notice for the preserved ``bijux-vex`` identity."""

from __future__ import annotations

import warnings

MESSAGE = (
    "bijux-vex is a compatibility name; use bijux-canon-index, import "
    "bijux_canon_index, and invoke bijux-canon-index for canonical behavior"
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
