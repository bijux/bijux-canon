"""Version helpers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

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
    from ._build_version import (  # type: ignore[attr-defined]
        __commit_id__,
        __version__,
        __version_tuple__,
        commit_id,
        version,
        version_tuple,
    )
except ImportError:

    def _fallback_version() -> str:
        """Handle fallback version."""
        try:
            return package_version("bijux-canon-reason")
        except PackageNotFoundError:
            return "0.3.0"

    def _version_parts(value: str) -> tuple[int | str, ...]:
        """Handle version parts."""
        tokens = value.replace("+", ".").replace("-", ".").split(".")
        return tuple(
            int(token) if token.isdigit() else token for token in tokens if token
        )

    __version__ = version = _fallback_version()
    __version_tuple__ = version_tuple = _version_parts(__version__)
    __commit_id__ = commit_id = None
