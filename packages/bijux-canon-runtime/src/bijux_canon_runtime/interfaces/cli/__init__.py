# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI exports for bijux-canon-runtime."""

from __future__ import annotations

from bijux_canon_runtime.interfaces.cli import entrypoint as _entrypoint_module
from bijux_canon_runtime.interfaces.cli.entrypoint import main

main._explain_failure = _entrypoint_module._explain_failure

__all__ = ["main"]
