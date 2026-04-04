---
title: Dependencies and Adjacencies
audience: mixed
type: guide
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-04-04
---

# Dependencies and Adjacencies

Package dependencies matter because they reveal which behavior is local and which behavior is delegated.

## Direct Dependency Themes

- pydantic
- typer
- fastapi

## Adjacent Package Relationships

- consumes evidence prepared by ingest and retrieval provided by index
- relies on runtime when a run must be accepted, stored, or replayed under policy

## Purpose

This page explains which surrounding tools and packages `bijux-canon-reason` depends on to do its job.

## Stability

Keep it aligned with `pyproject.toml` and the actual package seams.
