# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder

from bijux_vex.boundaries.api.app import build_app
from bijux_vex.core.canon import CANON_VERSION, canon
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.invariants import ALLOWED_METRICS
from bijux_vex.core.types import ExecutionArtifact
from bijux_vex.core.v1_exclusions import V1_EXCLUSIONS, ensure_excluded
from tests.e2e.api_smoke.test_openapi_freeze import EXPECTED_OPENAPI_FINGERPRINT
from tests.e2e.cli_workflows.test_cli_contract_freeze import CLI_HELP


def test_v1_release_gate():
    assert CANON_VERSION == "v1"
    assert ALLOWED_METRICS == {"l2", "cosine", "dot"}
    art = ExecutionArtifact(
        artifact_id="art",
        corpus_fingerprint="c",
        vector_fingerprint="v",
        metric="l2",
        scoring_version="v1",
        execution_contract=ExecutionContract.DETERMINISTIC,
    )
    assert art.schema_version == "v1"

    app = build_app()
    schema = jsonable_encoder(app.openapi())
    assert fingerprint(canon(schema)) == EXPECTED_OPENAPI_FINGERPRINT

    for feature in V1_EXCLUSIONS:
        with pytest.raises(NotImplementedError):
            ensure_excluded(feature)

    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    help_text = subprocess.check_output(
        [sys.executable, "-m", "bijux_vex.boundaries.cli.app", "--help"],
        text=True,
        env=env,
    )
    assert help_text == CLI_HELP
