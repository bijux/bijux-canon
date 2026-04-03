"""API boundary for Bijux Canon Agent."""

from __future__ import annotations

from .asgi import create_app

__all__ = ["create_app"]
