from __future__ import annotations

from collections.abc import Callable

import pytest

from bijux_canon_reason.interfaces.cli import compatibility


def test_legacy_rar_warns_before_canonical_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def canonical_app() -> None:
        calls.append("canonical")

    replacement: Callable[[], None] = canonical_app
    monkeypatch.setattr(compatibility, "app", replacement)

    with pytest.warns(FutureWarning, match="use bijux-canon-reason"):
        compatibility.legacy_rar()

    assert calls == ["canonical"]
