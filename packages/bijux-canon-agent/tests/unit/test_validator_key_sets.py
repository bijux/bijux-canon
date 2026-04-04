from __future__ import annotations

from bijux_canon_agent.agents.validator.rules.key_sets import (
    get_all_data_keys,
    get_all_schema_keys,
)


def test_get_all_schema_keys_tracks_nested_schema_paths() -> None:
    schema = {
        "user": {
            "schema": {
                "name": str,
                "profile": {"schema": {"age": int}},
            }
        }
    }

    assert get_all_schema_keys(schema) == {
        "user",
        "user.name",
        "user.profile",
        "user.profile.age",
    }


def test_get_all_data_keys_tracks_nested_payload_paths() -> None:
    data = {"user": {"name": "Ada", "profile": {"age": 42}}}

    assert get_all_data_keys(data) == {
        "user",
        "user.name",
        "user.profile",
        "user.profile.age",
    }
