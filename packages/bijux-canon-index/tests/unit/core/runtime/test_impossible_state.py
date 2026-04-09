# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any, cast

from bijux_canon_index.core.runtime.execution_session import ExecutionSession
import pytest


def test_execution_session_cannot_start_without_plan() -> None:
    with pytest.raises(TypeError):
        cast(Any, ExecutionSession)()
