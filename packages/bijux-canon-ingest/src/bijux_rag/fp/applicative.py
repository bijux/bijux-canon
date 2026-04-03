# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Backward-compatible name for Bijux RAG Validation.

The module-05 cores introduce Validation as an applicative; later cores refer to
it as `fp.validation`. This module keeps the earlier import path working.
"""

from __future__ import annotations

from .validation import *  # noqa: F403
