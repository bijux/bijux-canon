# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.application.source_discovery import (
    SourceDiscoveryRequest,
    discover_source_directory,
)


def test_source_discovery_boundary_returns_a_transport_neutral_manifest(
    tmp_path: Path,
) -> None:
    source = tmp_path / "evidence.txt"
    source.write_text("Ancient DNA evidence.\n", encoding="utf-8")

    outcome = discover_source_directory(
        SourceDiscoveryRequest(root_name="research", directory=tmp_path)
    )

    assert outcome.complete
    assert outcome.manifest["schema_version"] == "bijux.canon.ingest.discovery.v1"
    sources = outcome.manifest["sources"]
    assert isinstance(sources, list)
    assert sources[0]["relative_path"] == "evidence.txt"
