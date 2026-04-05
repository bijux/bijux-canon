# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
import os
import re
import subprocess
import sys
from pathlib import Path

CLI_HELP = """                                                                                
 Usage: python -m bijux_canon_index.interfaces.cli.app [OPTIONS] COMMAND        
                                                       [ARGS]...                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format          TEXT  Output format: json|table (default: json)            │
│ --output          PATH  Write output to a file                               │
│ --config          PATH  Load configuration from a TOML/YAML file             │
│ --trace                 Emit trace metadata                                  │
│ --quiet                 Suppress non-error output                            │
│ --no-color              Disable colored output                               │
│ --help                  Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list-artifacts                                                               │
│ list-runs                                                                    │
│ init                                                                         │
│ capabilities                                                                 │
│ audit                                                                        │
│ ingest                                                                       │
│ validate                                                                     │
│ doctor                                                                       │
│ materialize                                                                  │
│ execute                                                                      │
│ explain                                                                      │
│ replay                                                                       │
│ compare                                                                      │
│ bench                                                                        │
│ metrics                                                                      │
│ debug-bundle                                                                 │
│ vdb              Vector DB utilities                                         │
│ nd               ND utilities                                                │
│ config           Configuration utilities                                     │
│ artifact         Artifact bundle utilities                                   │
╰──────────────────────────────────────────────────────────────────────────────╯

"""


def _normalize_cli_help(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    normalized_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            normalized_lines.append("")
            continue
        if stripped.startswith(("╭", "╰")) and stripped.endswith(("╮", "╯")):
            continue
        if stripped.startswith("│") and stripped.endswith("│"):
            stripped = stripped[1:-1].strip()
        normalized_lines.append(re.sub(r"\s+", " ", stripped))
    return "\n".join(normalized_lines).strip() + "\n"


def test_cli_help_is_frozen():
    repo_root = Path(__file__).resolve().parents[3]
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "PYTHONPATH": str(repo_root / "src"),
        "TERM": "dumb",
    }
    out = subprocess.check_output(
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
    assert _normalize_cli_help(out) == _normalize_cli_help(CLI_HELP)
