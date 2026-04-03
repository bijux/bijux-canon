# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Concrete infrastructure adapters (end-of-Bijux RAG).

Infra contains effectful implementations of domain ports/capabilities.
Domain code must not import from infra; shells wire infra into the pure core.
"""
