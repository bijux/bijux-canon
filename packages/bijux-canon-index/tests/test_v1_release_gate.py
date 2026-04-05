# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.core.canon import CANON_VERSION, canon
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.identity.ids import fingerprint
from bijux_canon_index.core.invariants import ALLOWED_METRICS
from bijux_canon_index.core.types import ExecutionArtifact
from bijux_canon_index.core.v1_exclusions import V1_EXCLUSIONS, ensure_excluded
from tests.e2e.api_smoke.test_openapi_freeze import EXPECTED_OPENAPI_FINGERPRINT
from tests.e2e.cli_workflows.test_cli_contract_freeze import (
    CLI_HELP,
    _normalize_cli_help,
)


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
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "PYTHONPATH": str(repo_root / "src"),
        "TERM": "dumb",
    }
    help_text = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "bijux_canon_index.interfaces.cli.app",
            "--no-color",
            "--help",
        ],
        text=True,
        env=env,
    )
    assert _normalize_cli_help(help_text) == _normalize_cli_help(CLI_HELP)
