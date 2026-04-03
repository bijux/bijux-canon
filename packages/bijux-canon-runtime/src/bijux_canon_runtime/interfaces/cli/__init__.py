# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for cli/__init__.py."""

from __future__ import annotations

from bijux_canon_runtime.interfaces.cli import main as _main_module
from bijux_canon_runtime.interfaces.cli.main import main

main._explain_failure = _main_module._explain_failure

__all__ = ["main"]
