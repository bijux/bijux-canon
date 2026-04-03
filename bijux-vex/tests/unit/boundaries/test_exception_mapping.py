# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.boundaries.exception_bridge import to_cli_exit, to_http_status
from bijux_vex.core import errors


@pytest.mark.parametrize(
    "exc, status",
    [
        (errors.InvariantError(message="x"), 422),
        (errors.AuthzDeniedError(message="x"), 403),
        (errors.ValidationError(message="x"), 400),
    ],
)
def test_http_mapping(exc, status):
    assert to_http_status(exc) == status


@pytest.mark.parametrize(
    "exc, code",
    [
        (errors.InvariantError(message="x"), 3),
        (errors.AuthzDeniedError(message="x"), 6),
        (errors.ValidationError(message="x"), 2),
    ],
)
def test_cli_mapping(exc, code):
    assert to_cli_exit(exc) == code


def test_unknown_exception_raises():
    with pytest.raises(RuntimeError):
        to_http_status(RuntimeError("boom"))
