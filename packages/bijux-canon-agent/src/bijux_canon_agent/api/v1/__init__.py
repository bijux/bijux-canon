"""API v1 surface for Bijux Agent."""

from __future__ import annotations

from .http import build_router

API_VERSION = "v1"

__all__ = ["API_VERSION", "build_router"]
