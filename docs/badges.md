---
title: Badge Catalog
audience: maintainer
type: reference
status: canonical
owner: bijux-canon-dev
last_reviewed: 2026-04-11
---

# Badge Catalog

`docs/badges.md` is the single source of truth for shared badge templates across
the repository README surfaces. Update the named templates here, then run
`make sync-badges` so the root README, the docs landing page, and every public
package README publish the same badge contract.

Do not hand-edit badge blocks inside README files. Those files consume the
templates below through generated badge sections.

If a README surface needs package links outside the managed badge section, use
plain markdown links instead of inline badge markdown.

Generated badge sections always render in this order:

1. surface summary badges
2. one line of `PyPI` badges for every public package
3. one line of `GHCR` badges for every public package
4. one line of `Documentation` badges for the canonical `bijux-canon-*` packages

Link policy for GHCR badges is fixed here as part of the contract:

- the repository-wide GHCR summary badge links to
  `https://github.com/bijux?tab=packages&repo_name=bijux-canon`
- per-package GHCR badges link to the package-specific
  `https://github.com/bijux/bijux-canon/pkgs/container/...` page

## Repository Summary

<!-- bijux-canon-badges:repository-summary:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/bijux-canon-runtime/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![Verify](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![Publish](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/publish.yml)
[![Docs](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/deploy-docs.yml)
[![Release](https://img.shields.io/github/v/release/bijux/bijux-canon?display_name=tag&label=release)](https://github.com/bijux/bijux-canon/releases)
[![GHCR packages](https://img.shields.io/badge/ghcr-{{ public_package_count }}%20packages-181717?logo=github)](https://github.com/bijux?tab=packages&repo_name=bijux-canon)
[![Published packages](https://img.shields.io/badge/published%20packages-{{ public_package_count }}-2563EB)](https://github.com/bijux/bijux-canon/tree/main/packages)
<!-- bijux-canon-badges:repository-summary:end -->

## Package Summary

<!-- bijux-canon-badges:package-summary:start -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)]({{ package_pypi_url }})
[![Typing: typed](https://img.shields.io/badge/typing-typed%20(PEP%20561)-0A7BBB)]({{ package_pypi_url }})
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0F766E)](https://github.com/bijux/bijux-canon/blob/main/LICENSE)
[![CI Status](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml/badge.svg)](https://github.com/bijux/bijux-canon/actions/workflows/verify.yml)
[![GitHub Repository](https://img.shields.io/badge/github-bijux%2Fbijux--canon-181717?logo=github)](https://github.com/bijux/bijux-canon)
<!-- bijux-canon-badges:package-summary:end -->

## Family PyPI Badge

<!-- bijux-canon-badges:family-pypi-badge:start -->
[![{{ distribution_name }}](https://img.shields.io/pypi/v/{{ distribution_name }}?label={{ pypi_badge_label }}&logo=pypi)]({{ package_pypi_url }})
<!-- bijux-canon-badges:family-pypi-badge:end -->

## Family GHCR Badge

<!-- bijux-canon-badges:family-ghcr-badge:start -->
[![{{ distribution_name }}](https://img.shields.io/badge/{{ pypi_badge_label }}-ghcr-181717?logo=github)]({{ package_ghcr_url }})
<!-- bijux-canon-badges:family-ghcr-badge:end -->

## Family Docs Badge

<!-- bijux-canon-badges:family-docs-badge:start -->
[![{{ docs_badge_alt }}](https://img.shields.io/badge/docs-{{ docs_badge_label }}-2563EB?logo=materialformkdocs&logoColor=white)]({{ docs_url }})
<!-- bijux-canon-badges:family-docs-badge:end -->
