# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_runtime.application.non_determinism_lifecycle import (
    NonDeterminismLifecycle as ApplicationLifecycle,
)
from bijux_canon_runtime.runtime.non_determinism_lifecycle import (
    NonDeterminismLifecycle as RuntimeLifecycle,
)


def test_application_reexport_points_to_runtime_lifecycle() -> None:
    assert ApplicationLifecycle is RuntimeLifecycle
