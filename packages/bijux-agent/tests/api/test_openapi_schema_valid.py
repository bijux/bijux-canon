"""Validate OpenAPI schema for API v1."""

from __future__ import annotations

from pathlib import Path

from openapi_spec_validator import validate
import yaml


def test_openapi_schema_valid() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "api" / "v1" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    validate(schema)
