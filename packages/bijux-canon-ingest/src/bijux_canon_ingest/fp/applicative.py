# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility alias for the validation module.

`fp.validation` is the canonical import path. This module keeps the older
`fp.applicative` entry point working for downstream callers.
"""

from __future__ import annotations

from .validation import (
    Validation,
    VFailure,
    VSuccess,
    compose,
    dedup_stable,
    from_validation,
    to_validation,
    v_ap,
    v_failure,
    v_liftA2,
    v_liftA3,
    v_map,
    v_pure,
    v_sequence,
    v_success,
    v_traverse,
)

__all__ = [
    "Validation",
    "VSuccess",
    "VFailure",
    "v_pure",
    "v_success",
    "v_failure",
    "v_map",
    "v_ap",
    "v_liftA2",
    "v_liftA3",
    "v_sequence",
    "v_traverse",
    "to_validation",
    "from_validation",
    "dedup_stable",
    "compose",
]
