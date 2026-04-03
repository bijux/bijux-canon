"""API boundary for Bijux Canon Agent."""

from __future__ import annotations

from .v1 import API_VERSION, create_app

__all__ = ["API_VERSION", "create_app"]
