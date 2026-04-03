from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bijux_agent.config.defaults import MINIMAL_REFERENCE_CONFIG, PIPELINE_DEFAULTS


def _hash_defaults() -> str:
    payload = {
        "pipeline": PIPELINE_DEFAULTS,
        "minimal_reference": MINIMAL_REFERENCE_CONFIG,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _fallback_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("fallback-version"):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("fallback-version not found in pyproject.toml")


def test_defaults_hash_is_stable() -> None:
    snapshot_path = (
        Path(__file__).resolve().parents[1] / "snapshots" / "defaults_versioning.json"
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["defaults_hash"] == _hash_defaults()
    assert snapshot["fallback_version"] == _fallback_version()
