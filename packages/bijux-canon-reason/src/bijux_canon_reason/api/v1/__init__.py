# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> Any:
    if name == "app":
        from bijux_canon_reason.api.v1.app import app

        return app
    if name == "create_app":
        from bijux_canon_reason.api.v1.app import create_app

        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
