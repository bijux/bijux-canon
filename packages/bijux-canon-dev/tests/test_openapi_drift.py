from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.api.openapi_drift import canonicalize, load_target, write_schema


class _FakeApp:
    def openapi(self) -> dict[str, object]:
        return {"openapi": "3.1.0", "info": {"title": "fake", "version": "v1"}}


def test_load_target_calls_factory(monkeypatch) -> None:
    module = ModuleType("test_fake_app")
    module.create_app = _FakeApp
    monkeypatch.setitem(sys.modules, "test_fake_app", module)

    app = load_target("test_fake_app:create_app")

    assert isinstance(app, _FakeApp)


def test_write_schema_supports_yaml(tmp_path) -> None:
    schema_path = tmp_path / "schema.yaml"
    payload = {"openapi": "3.1.0", "info": {"title": "fake", "version": "v1"}}

    write_schema(schema_path, payload)

    assert yaml.safe_load(schema_path.read_text(encoding="utf-8")) == payload


def test_canonicalize_normalizes_tuples() -> None:
    payload = {"items": ("a", "b")}

    assert canonicalize(payload) == {"items": ["a", "b"]}
