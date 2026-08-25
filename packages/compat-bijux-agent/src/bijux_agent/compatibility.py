"""Compatibility notice for the preserved ``bijux-agent`` identity."""

from __future__ import annotations

import warnings

MESSAGE = (
    "bijux-agent is a compatibility name; use bijux-canon-agent, import "
    "bijux_canon_agent, and invoke bijux-canon-agent for canonical behavior"
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
