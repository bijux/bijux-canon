---
title: Documentation Standards
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-26
---

# Documentation Standards

Documentation standards for `bijux-canon-reason` should keep the handbook reader-first, direct, and evidence-backed. Consistency matters only when it helps readers trust what they are being told.

## What To Check

- prefer durable filenames and headings that name the real question the page answers
- tie prose to code paths, artifacts, contracts, or tests instead of abstract template language
- treat filler, meta-doc prose, and unsupported certainty as documentation defects

## First Proof Check

- `tests` and package-local validation surfaces for executable evidence
- caller-facing docs, limits, and risks for the trust story readers actually receive
- release notes and change records when the work alters what others may safely assume

## Bottom Line

If `bijux-canon-reason` cannot explain why `reasoning and verification behavior` should be trusted after a change, the quality work is still incomplete.
