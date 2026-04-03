# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from importlib import metadata
import re
import tomllib
from pathlib import Path

import typer.main

from bijux_canon_reason import __version__
from bijux_canon_reason.boundaries.cli.main import app
from bijux_canon_reason.core.rar_types import Claim, EvidenceRef, ProblemSpec, SupportRef


def test_version_matches_pyproject() -> None:
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    pyproject_version = project.get("version")
    dynamic_fields = set(project.get("dynamic", []))
    hatch_fallback_version = (
        data.get("tool", {}).get("hatch", {}).get("version", {}).get("fallback-version")
    )

    ver_file = root / "src" / "bijux_canon_reason" / "_version.py"
    placeholder_version = None
    m = re.search(
        r"__version__\s*=\s*['\"](?P<v>[^'\"]+)['\"]",
        ver_file.read_text(encoding="utf-8"),
    )
    if m:
        placeholder_version = m.group("v")

    def _base(v: str | None) -> str:
        if not v:
            return ""
        # normalize dev / local tags to base prefix
        return v.split("+", 1)[0].split(".dev", 1)[0]

    try:
        dist_version = metadata.version("bijux-canon-reason")
    except metadata.PackageNotFoundError:
        try:
            dist_version = metadata.version("bijux-rar")
        except metadata.PackageNotFoundError:
            dist_version = __version__

    if "version" in dynamic_fields:
        candidates = [placeholder_version, dist_version, __version__]
        if not dist_version and hatch_fallback_version:
            candidates.append(hatch_fallback_version)
        assert _base(dist_version), "distribution version could not be resolved"
    else:
        candidates = [pyproject_version, placeholder_version, dist_version, __version__]

    bases = [b for b in (_base(v) for v in candidates) if b]
    assert bases, "no version candidates found"
    assert len(set(bases)) == 1, f"version mismatch bases={bases}"


def test_cli_surface_and_models_are_frozen() -> None:
    command: typer.main.TyperGroup = typer.main.get_command(app)
    assert set(command.commands.keys()) == {"run", "verify", "replay", "eval"}

    def _opts(cmd_name: str) -> set[str]:
        params = command.commands[cmd_name].params
        return {
            opt
            for p in params
            for opt in p.opts
            if p.name != "help" and opt.startswith("--")
        }

    # Run command is frozen; opts must match exactly (order-agnostic).
    assert _opts("run") == {
        "--spec",
        "--preset",
        "--seed",
        "--artifacts-dir",
        "--fail-on-verify",
        "--json",
    }
    # Verify/replay/eval must expose required flags.
    assert "--trace" in _opts("verify")
    assert "--trace" in _opts("replay")
    assert "--suite" in _opts("eval")

    # Guard critical model field sets to prevent accidental API drift.
    assert set(ProblemSpec.model_fields) == {
        "id",
        "description",
        "constraints",
        "expected_output_type",
        "expected",
        "version",
    }
    assert set(EvidenceRef.model_fields) == {
        "id",
        "uri",
        "sha256",
        "span",
        "content_path",
        "chunk_id",
    }
    assert set(SupportRef.model_fields) == {
        "kind",
        "ref_id",
        "span",
        "snippet_sha256",
        "hash_algo",
    }
    assert set(Claim.model_fields) >= {
        "id",
        "statement",
        "status",
        "confidence",
        "supports",
        "claim_type",
        "structured",
    }
