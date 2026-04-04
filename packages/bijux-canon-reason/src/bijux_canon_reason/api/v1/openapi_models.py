# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Liveness indicator returned by the API.")


class ErrorDetail(BaseModel):
    detail: str = Field(description="Human-readable explanation for the API failure.")


class ItemResponse(BaseModel):
    id: int = Field(ge=1, description="Stable item identifier.")
    name: str = Field(description="Reader-facing item name.")
    description: str = Field(description="Free-form item description.")


class ItemListResponse(BaseModel):
    items: list[ItemResponse] = Field(
        description="Ordered page of active items returned by the API."
    )
    total: int = Field(ge=0, description="Total number of active items available.")


__all__ = [
    "ErrorDetail",
    "HealthResponse",
    "ItemListResponse",
    "ItemResponse",
]
