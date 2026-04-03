# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from bijux_vex.infra.run_store import RunStore


def test_run_store_records_refusal_details(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path)
    run_id = "run-1"
    store.start(run_id, {"seed": "demo"})
    details = {"reason": "configuration_error", "message": "bad config"}
    store.mark_failed(run_id, "failed", details=details)

    payload = json.loads((tmp_path / run_id / "status.json").read_text())
    assert payload["status"] == "failed"
    assert payload["details"] == details
