# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/__init__.py."""

from __future__ import annotations

from agentic_flows.spec.model import *  # noqa: F403
from agentic_flows.spec.model import __all__ as _model_all
from agentic_flows.spec.ontology import *  # noqa: F403
from agentic_flows.spec.ontology import __all__ as _ontology_all

__all__ = [*_model_all, *_ontology_all]
