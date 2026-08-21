# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# Shared fixtures live here when needed.

from pathlib import Path
import sys

import pytest

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))


@pytest.fixture()
def corpus_fixture() -> Path:
    """Return the explicitly selected corpus used by retrieval tests."""
    return TESTS_ROOT / "fixtures" / "corpus_small.jsonl"
