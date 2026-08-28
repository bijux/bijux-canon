# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

RUNTIME_SOURCE = Path(__file__).resolve().parents[3] / "src"


def test_application_operations_are_importable_before_runtime_services(
    tmp_path: Path,
) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(RUNTIME_SOURCE)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from bijux_canon_runtime.application.operations import "
                "RuntimeApplicationServicesV2; "
                "from bijux_canon_runtime.runtime.replay import RuntimeReplayService; "
                "from bijux_canon_runtime.runtime.execution import "
                "compose_runtime_application_services; "
                "assert RuntimeApplicationServicesV2.capability.service_version == '2.0'; "
                "assert RuntimeReplayService.__name__ == 'RuntimeReplayService'; "
                "assert callable(compose_runtime_application_services)"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_v2_api_is_importable_in_a_fresh_process(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(RUNTIME_SOURCE)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from bijux_canon_runtime.api.v2.app import create_app; "
                "from bijux_canon_runtime.application.readiness import "
                "ReadinessCapability; "
                "assert create_app().openapi()['openapi'] == '3.1.0'; "
                "assert ReadinessCapability.INGEST.value == 'ingest'"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
