# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Pydantic-at-the-edges models and codecs (end-of-Bijux RAG; adapters).

# pyright: reportUnknownArgumentType=false
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, computed_field, model_validator

from bijux_rag.fp.core import Chunk, make_chunk

T = TypeVar("T")

StrictConfig = ConfigDict(
    strict=True,
    frozen=True,
    extra="forbid",
    populate_by_name=True,
)


class ChunkModel(BaseModel):
    model_config = StrictConfig

    version: Literal[1] = 1
    text: str = Field(min_length=1, max_length=200_000)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] | None = None

    @model_validator(mode="after")
    def _validate_embedding(self) -> "ChunkModel":
        if self.embedding is None:
            return self
        if not self.embedding:
            raise ValueError("embedding must be non-empty if present")
        if len(self.embedding) > 8192:
            raise ValueError("embedding too long")
        for i, v in enumerate(self.embedding):
            if not math.isfinite(v):
                raise ValueError(f"embedding[{i}] not finite")
            if abs(v) > 100.0:
                raise ValueError(f"embedding[{i}] out of reasonable range")
        return self

    @computed_field
    def length(self) -> int:
        return len(self.text)


def to_core_chunk(model: ChunkModel) -> Chunk:
    return make_chunk(text=model.text, path=(), metadata=model.metadata)


def from_core_chunk(core: Chunk) -> ChunkModel:
    return ChunkModel(text=core.text, metadata=dict(core.metadata))


def serialize_model(model: BaseModel) -> str:
    computed = getattr(model.__class__, "model_computed_fields", {})
    computed_keys = list(computed.keys()) if isinstance(computed, dict) else []
    exclude: set[str] = set(str(k) for k in computed_keys)
    return model.model_dump_json(by_alias=True, exclude_unset=True, exclude=exclude)


def deserialize_model(json_str: str, typ: type[T]) -> T:
    return TypeAdapter(typ).validate_json(json_str)


__all__ = [
    "ChunkModel",
    "to_core_chunk",
    "from_core_chunk",
    "serialize_model",
    "deserialize_model",
]
