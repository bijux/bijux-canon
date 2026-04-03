"""Invariant: API version marker is present."""

from __future__ import annotations

from bijux_agent.api import v1


def test_api_version_marker_exists() -> None:
    assert isinstance(v1.API_VERSION, str)
    assert v1.API_VERSION == "v1"
