# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility alias for the validation module.

`fp.validation` is the canonical import path. This module keeps the older
`fp.applicative` entry point working for downstream callers.
"""

from __future__ import annotations

from .validation import *  # noqa: F403
