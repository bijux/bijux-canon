# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import asdict

from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)


def test_replay_envelope_canary(replay_envelope) -> None:
    expected = "7688f19c3c38620684014aab1499d53c4a2afc8e74e535b1ba7976a80dbfcc57"
    assert fingerprint_inputs(asdict(replay_envelope)) == expected
