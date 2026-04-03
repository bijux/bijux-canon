from __future__ import annotations

from pathlib import Path
import re

BANNED_WORDS = {"autonomous", "intelligent", "emergent", "magic"}
ALLOWED_PATHS = {
    Path("docs/packages/bijux-canon-agent/maintainer/anti-features.md"),
    Path("docs/packages/bijux-canon-agent/maintainer/docs_voice.md"),
}


def test_docs_avoid_banned_words() -> None:
    """Ensure the documentation tone stays disciplined."""
    pattern = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.IGNORECASE)
    roots = [
        Path("docs/packages/bijux-canon-agent"),
        Path("packages/bijux-canon-agent/docs"),
    ]
    for root in roots:
        for path in root.rglob("*.md"):
            if path in ALLOWED_PATHS:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                raise AssertionError(
                    f"{path} contains banned words; replace them with normative language"
                )
