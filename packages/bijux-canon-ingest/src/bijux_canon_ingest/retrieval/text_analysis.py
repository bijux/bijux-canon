# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic text normalization for lexical retrieval."""

from __future__ import annotations

from hashlib import sha256


def stable_token_bucket(token: str, *, buckets: int) -> int:
    digest = sha256(token.encode("utf-8")).digest()
    number = int.from_bytes(digest[:8], "big", signed=False)
    return int(number % buckets)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


__all__ = ["stable_token_bucket", "tokenize"]
