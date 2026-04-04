# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Concrete infrastructure adapters.

Infra contains effectful implementations of domain ports/capabilities.
Domain code must not import from infra; shells wire infra into the pure core.
"""
