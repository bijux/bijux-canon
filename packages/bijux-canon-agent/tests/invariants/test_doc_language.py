from __future__ import annotations

from pathlib import Path
import re

BANNED_WORDS = {"autonomous", "intelligent", "emergent", "magic"}
ALLOWED_PATHS = {
    Path("docs/governance/anti-features.md"),
    Path("docs/docs-voice.md"),
}


def test_docs_avoid_banned_words() -> None:
    """Ensure the documentation tone stays disciplined."""
    pattern = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.IGNORECASE)
    for path in Path("docs").rglob("*.md"):
        if path in ALLOWED_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            raise AssertionError(
                f"{path} contains banned words; replace them with normative language"
            )
