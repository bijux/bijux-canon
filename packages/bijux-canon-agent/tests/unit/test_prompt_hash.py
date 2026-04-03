from __future__ import annotations

from bijux_canon_agent.support.hashing import prompt_hash


def test_prompt_hash_is_deterministic() -> None:
    prompt = "Once upon a time."
    assert prompt_hash(prompt) == prompt_hash(prompt)
    assert prompt_hash(f"  {prompt}  ") == prompt_hash(prompt)


def test_prompt_hash_handles_unicode_normalization() -> None:
    base = "café"
    decomposed = "cafe\u0301"
    assert prompt_hash(base) == prompt_hash(decomposed)
