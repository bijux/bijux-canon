# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_index.core.errors import ValidationError


DEFAULT_CONFIG_TEMPLATE = """[vector_store]
backend = "memory"
# uri = "index.faiss"

[embeddings]
provider = "sentence_transformers"
model = "all-MiniLM-L6-v2"

[resource_limits]
# max_vectors_per_ingest = 10000
# max_k = 50
# max_query_size = 10000
# max_execution_time_ms = 2000
"""


def initialize_workspace(config_path: Path, *, force: bool) -> dict[str, str]:
    if config_path.exists() and not force:
        raise ValidationError(message="Config already exists. Use --force to overwrite.")
    config_path.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    for folder in (
        Path("artifacts") / "bijux-canon-index",
        Path("artifacts") / "bijux-canon-index" / "runs",
    ):
        folder.mkdir(parents=True, exist_ok=True)
    ensure_gitignore_entries(
        Path(".gitignore"),
        entries=("artifacts/", "*.sqlite", "*.faiss", "*.meta.json"),
    )
    return {"status": "initialized", "config": str(config_path)}


def ensure_gitignore_entries(gitignore_path: Path, *, entries: tuple[str, ...]) -> None:
    lines: list[str] = []
    if gitignore_path.exists():
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    for entry in entries:
        if entry not in lines:
            lines.append(entry)
    gitignore_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = ["DEFAULT_CONFIG_TEMPLATE", "ensure_gitignore_entries", "initialize_workspace"]
