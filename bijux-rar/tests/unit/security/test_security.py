# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_rar.security import rate_limit_per_key, rate_limit_stateful, require_api_key, sanitize_run_id


def test_sanitize_run_id_accepts_safe_ids() -> None:
    assert sanitize_run_id("abc-123") == "abc-123"


def test_sanitize_run_id_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        sanitize_run_id("../bad")


def test_rate_limit_stateful_blocks_after_limit() -> None:
    state = {"limit": 2, "window_start": 0.0, "count": 0}
    rate_limit_stateful(state)
    rate_limit_stateful(state)
    with pytest.raises(PermissionError):
        rate_limit_stateful(state)


def test_rate_limit_per_key_blocks_per_key() -> None:
    state = {"limit": 1}
    rate_limit_per_key(state, "k1")
    with pytest.raises(PermissionError):
        rate_limit_per_key(state, "k1")
    # different key allowed
    rate_limit_per_key(state, "k2")


def test_require_api_key_checks_header() -> None:
    headers = {"x-api-key": "secret"}
    require_api_key(headers, expected="secret")
    with pytest.raises(PermissionError):
        require_api_key(headers, expected="other")
