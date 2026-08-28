# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Public CLI restart coverage for equivalent workspace path spelling."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import materialize_model


def _materialized_model(root: Path) -> Path:
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch_artifact(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    materialize_model(
        LOCAL_MINILM_PROFILE,
        root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch_artifact,
    )
    return root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision


def _run_init(*, cwd: Path, workspace: str, model: str) -> dict[str, object]:
    command = Path(sys.executable).with_name("bijux-canon-runtime")
    result = subprocess.run(
        [
            str(command),
            "init",
            "--workspace",
            workspace,
            "--model",
            model,
            "--json",
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def test_installed_cli_reopens_relative_workspace_by_absolute_path_after_restart(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path / "model-cache")
    workspace = tmp_path / "state" / "workspace"
    second_process_cwd = tmp_path / "another-cwd"
    second_process_cwd.mkdir()

    initialized = _run_init(
        cwd=tmp_path,
        workspace="state/../state/workspace",
        model=str(model.relative_to(tmp_path)),
    )
    reopened = _run_init(
        cwd=second_process_cwd,
        workspace=str(workspace),
        model=str(model),
    )

    assert initialized["status"] == "initialized"
    assert reopened["status"] == "unchanged"
    assert reopened["workspace_root"] == str(workspace)
    assert reopened["workspace_id"] == initialized["workspace_id"]
    assert (
        reopened["configuration_identity_sha256"]
        == (initialized["configuration_identity_sha256"])
    )
    assert reopened["layout_identity_sha256"] == initialized["layout_identity_sha256"]
