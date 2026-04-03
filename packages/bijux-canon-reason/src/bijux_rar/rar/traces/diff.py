# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.rar_types import Trace


def diff_traces(a: Trace, b: Trace) -> dict[str, object]:
    """Compare two traces structurally and return a dict summary."""
    a_events = [e.model_dump(mode="json") for e in a.events]
    b_events = [e.model_dump(mode="json") for e in b.events]

    first = None
    for i, (ea, eb) in enumerate(zip(a_events, b_events, strict=False)):
        if ea != eb:
            first = i
            break
    if first is None and len(a_events) != len(b_events):
        first = min(len(a_events), len(b_events))

    changed: dict[str, int] = {}
    if first is not None:
        for ev in a_events[first:] + b_events[first:]:
            k = str(ev.get("kind"))
            changed[k] = changed.get(k, 0) + 1

    return {
        "identical": first is None and len(a_events) == len(b_events),
        "first_mismatch_idx": first,
        "changed_event_kinds": changed,
        "original_event": None if first is None else a_events[first],
        "replayed_event": None if first is None else b_events[first],
    }
