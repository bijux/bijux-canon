# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""Concrete infrastructure adapters (end-of-Bijux RAG).

Infra contains effectful implementations of domain ports/capabilities.
Domain code must not import from infra; shells wire infra into the pure core.
"""
