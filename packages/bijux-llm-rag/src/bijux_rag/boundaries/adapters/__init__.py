# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Boundary adapters (end-of-Bijux RAG).

This subpackage groups reusable "edge adapters":
- Serialization (`serde`)
- Pydantic-at-the-edges codecs (`pydantic_edges`)
- Exception bridging to Result/Validation (`exception_bridge`)
"""

from .exception_bridge import (
    UnexpectedFailure,
    result_map_try,
    try_result,
    unexpected_fail,
    v_map_try,
    v_try,
)
from .pydantic_edges import ChunkModel, deserialize_model, serialize_model
from .serde import Envelope, from_json, to_json

__all__ = [
    # serde
    "Envelope",
    "to_json",
    "from_json",
    # pydantic edges
    "ChunkModel",
    "serialize_model",
    "deserialize_model",
    # exception bridge
    "try_result",
    "result_map_try",
    "v_try",
    "v_map_try",
    "UnexpectedFailure",
    "unexpected_fail",
]
