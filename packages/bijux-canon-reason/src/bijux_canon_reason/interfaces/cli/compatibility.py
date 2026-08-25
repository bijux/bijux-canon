# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Compatibility entrypoints retained by canonical Reason metadata."""

from __future__ import annotations

import warnings

from bijux_canon_reason.interfaces.cli import app

_RAR_MESSAGE = (
    "bijux-rar is a compatibility name; use bijux-canon-reason, import "
    "bijux_canon_reason, and invoke bijux-canon-reason for canonical behavior"
)


def legacy_rar() -> None:
    """Warn before dispatching the preserved ``bijux-rar`` command."""
    warnings.warn(_RAR_MESSAGE, FutureWarning, stacklevel=2)
    app()


__all__ = ["legacy_rar"]
