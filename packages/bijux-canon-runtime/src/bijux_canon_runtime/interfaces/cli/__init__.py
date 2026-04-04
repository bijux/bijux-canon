# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI exports for bijux-canon-runtime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from bijux_canon_runtime.interfaces.cli import entrypoint as _entrypoint_module


class _MainEntrypoint(Protocol):
    """CLI main entrypoint contract used by tests."""

    _explain_failure: Callable[..., None]

    def __call__(self) -> None:
        """Invoke the runtime CLI entrypoint."""
        ...


main = cast(_MainEntrypoint, _entrypoint_module.main)
main._explain_failure = _entrypoint_module._explain_failure

__all__ = ["main"]
