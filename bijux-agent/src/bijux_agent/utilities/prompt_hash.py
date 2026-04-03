"""Deterministic prompt hashing utilities used across LLM integrations."""

from __future__ import annotations

import hashlib
import unicodedata


def prompt_hash(prompt: str) -> str:
    """Return a stable sha256 hash for a given prompt text (NFC-normalized)."""

    normalized = unicodedata.normalize("NFC", prompt.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
