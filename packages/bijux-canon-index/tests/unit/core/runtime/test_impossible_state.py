# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any, cast

import pytest

from bijux_canon_index.core.runtime.execution_session import ExecutionSession


def test_execution_session_cannot_start_without_plan() -> None:
    with pytest.raises(TypeError):
        cast(Any, ExecutionSession)()
