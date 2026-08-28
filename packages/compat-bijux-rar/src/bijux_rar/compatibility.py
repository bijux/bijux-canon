"""Compatibility notice for the preserved ``bijux-rar`` identity."""

from __future__ import annotations

import warnings

MESSAGE = (
    "bijux-rar is a compatibility name; use bijux-canon-reason, import "
    "bijux_canon_reason, and invoke bijux-canon-reason for canonical behavior"
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
