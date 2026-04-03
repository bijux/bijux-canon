# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility import surface for the former ``bijux_rag`` package name."""

from __future__ import annotations

import bijux_canon_ingest as _impl

__path__ = _impl.__path__

for _name in dir(_impl):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_impl, _name)

_impl_all = getattr(_impl, "__all__", ())
__all__ = [name for name in _impl_all if hasattr(_impl, name)]
