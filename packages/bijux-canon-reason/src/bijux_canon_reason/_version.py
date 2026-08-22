"""Version helpers."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import cast

__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
    "__commit_id__",
    "commit_id",
]

version: str
__version__: str
__version_tuple__: tuple[int | str, ...]
version_tuple: tuple[int | str, ...]
commit_id: str | None
__commit_id__: str | None

try:
    _build_version = import_module(f"{__package__}._build_version")
except ImportError:

    def _fallback_version() -> str:
        """Handle fallback version."""
        try:
            return package_version("bijux-canon-reason")
        except PackageNotFoundError:
            return "0.3.9"

    def _version_parts(value: str) -> tuple[int | str, ...]:
        """Handle version parts."""
        tokens = value.replace("+", ".").replace("-", ".").split(".")
        return tuple(
            int(token) if token.isdigit() else token for token in tokens if token
        )

    __version__ = version = _fallback_version()
    __version_tuple__ = version_tuple = _version_parts(__version__)
    __commit_id__ = commit_id = None
else:
    __version__ = version = cast(str, _build_version.__version__)
    __version_tuple__ = version_tuple = cast(
        tuple[int | str, ...], _build_version.__version_tuple__
    )
    __commit_id__ = commit_id = cast(str | None, _build_version.__commit_id__)
