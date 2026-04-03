# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

import bijux_canon_runtime
from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from bijux_canon_runtime.model.flows.manifest import FlowManifest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    assert execute_flow
    assert ExecutionConfig
    assert RunMode
    assert FlowManifest
    assert set(bijux_canon_runtime.__all__) == {"FlowManifest", "RunMode", "execute_flow"}
