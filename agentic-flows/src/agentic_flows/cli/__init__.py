# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for cli/__init__.py."""

from __future__ import annotations

from agentic_flows.cli import main as _main_module
from agentic_flows.cli.main import main

main._explain_failure = _main_module._explain_failure

__all__ = ["main"]
